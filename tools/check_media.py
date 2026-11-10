"""Verify an encoded BlockReel MP4 against its delivery brief (requires ffprobe)."""

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def positive_fraction(value):
    try:
        number = Fraction(value)
        if number > 0:
            return number
    except (ValueError, ZeroDivisionError):
        pass
    raise argparse.ArgumentTypeError("expected a positive number or fraction")


def dimensions(value):
    try:
        width, height = map(int, value.lower().split("x"))
        if width > 0 and height > 0:
            return width, height
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected dimensions such as 1280x720")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--duration", type=positive_fraction, required=True, help="target seconds")
    parser.add_argument("--size", type=dimensions, required=True, help="target WIDTHxHEIGHT")
    parser.add_argument("--fps", type=positive_fraction, required=True, help="target rate (e.g. 24 or 30000/1001)")
    parser.add_argument("--require-audio", action="store_true", help="require audio covering the picture timeline")
    args = parser.parse_args(argv)
    expected_frames = args.duration * args.fps
    if expected_frames.denominator != 1:
        parser.error("--duration and --fps must correspond to a whole number of frames")

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(args.video.resolve())],
            check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        streams = json.loads(result.stdout)["streams"]
    except FileNotFoundError:
        print("FAIL: ffprobe is not available on PATH", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: {exc.stderr.strip()}", file=sys.stderr)
        return 1

    video = next((s for s in streams if s["codec_type"] == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        print("FAIL: no picture stream", file=sys.stderr)
        return 1

    try:
        rate = Fraction(video["avg_frame_rate"])
        length = Fraction(video["duration"])
        frames = int(video["nb_frames"])
        size = video["width"], video["height"]
    except (KeyError, ValueError, ZeroDivisionError):
        print("FAIL: incomplete picture stream metadata", file=sys.stderr)
        return 1

    issues = []
    if size != args.size:
        issues.append(f"picture dimensions {size[0]}x{size[1]} differ from {args.size[0]}x{args.size[1]}")
    if rate != args.fps or frames != expected_frames:
        issues.append(f"{frames} frames at {rate} fps, expected {expected_frames} at {args.fps} fps")
    if abs(length - args.duration) > Fraction(1, 1000):
        issues.append(f"picture duration {float(length):.6f}s, expected {float(args.duration):.6f}s")

    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    audio_status = audio["codec_name"] if audio else "no audio"
    if args.require_audio:
        if audio is None:
            issues.append("no audio stream")
        else:
            try:
                start = Fraction(audio["start_time"]) - Fraction(video["start_time"])
                end = start + Fraction(audio["duration"])
                tolerance = max(1 / args.fps, Fraction(3, 100))
                if abs(start) > tolerance or abs(end - length) > tolerance:
                    issues.append(f"audio covers {float(start):.3f}s to {float(end):.3f}s of {float(length):.3f}s")
            except (KeyError, ValueError, ZeroDivisionError):
                issues.append("incomplete audio timing metadata")

    if issues:
        for issue in issues:
            print(f"FAIL: {issue}", file=sys.stderr)
        return 1
    print(f"PASS: {size[0]}x{size[1]}, {frames} frames at {rate} fps, {float(length):.3f}s, {audio_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
