// Post-processing: bloom, rack-focus depth of field, colour grade, film grain, chromatic aberration.
// Config (style.post, story.post, and per-shot camera.post, merged in that order):
//   bloom: { strength, radius, threshold }      grade: { exposure, contrast, saturation, tint:[r,g,b], lift:[r,g,b], gain:[r,g,b] }
//   grain: 0..0.2      chroma: 0..0.01      dof: { focus (blocks), aperture, maxblur }
// Grain is seeded by the frame time, so renders stay deterministic.
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const GRADE = {
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, res: { value: null }, exposure: { value: 1 }, contrast: { value: 1 }, saturation: { value: 1 },
    grain: { value: 0 }, chroma: { value: 0 }, tint: { value: null }, lift: { value: null }, gain: { value: null },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uTime, exposure, contrast, saturation, grain, chroma; uniform vec2 res; uniform vec3 tint, lift, gain; varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main(){
      vec2 d = vUv - 0.5; vec3 c;
      c.r = texture2D(tDiffuse, vUv + d * chroma).r; c.g = texture2D(tDiffuse, vUv).g; c.b = texture2D(tDiffuse, vUv - d * chroma).b;
      c *= exposure; c = (c - 0.5) * contrast + 0.5;
      float l = dot(c, vec3(0.299, 0.587, 0.114)); c = mix(vec3(l), c, saturation);
      c = c * tint * gain + lift * (1.0 - c);
      c += (hash(floor(vUv * res) + fract(uTime * 7.31) * 113.0) - 0.5) * grain;
      gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
    }`,
};

const merge = (...os) => { const out = {}; for (const o of os) for (const [k, v] of Object.entries(o || {})) out[k] = (v && typeof v === 'object' && !Array.isArray(v)) ? { ...(out[k] || {}), ...v } : v; return out; };

export function usesPost(...cfgs) { const m = merge(...cfgs); return !!(m.bloom || m.grade || m.grain || m.chroma || m.dof); }

export function createPost(THREE, renderer, scene, camera, W, H, allCfgs) {
  const any = merge(...allCfgs);
  const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, rt);
  composer.setSize(W, H);
  composer.addPass(new RenderPass(scene, camera));
  const bokeh = any.dof ? new BokehPass(scene, camera, { focus: 10, aperture: 0.0002, maxblur: 0.01 }) : null; if (bokeh) composer.addPass(bokeh);
  const bloom = any.bloom ? new UnrealBloomPass(new THREE.Vector2(W, H), 0.6, 0.5, 0.85) : null; if (bloom) composer.addPass(bloom);
  composer.addPass(new OutputPass()); // tone/colour-space conversion to sRGB
  const grade = new ShaderPass({ ...GRADE, uniforms: THREE.UniformsUtils.clone(GRADE.uniforms) });
  grade.uniforms.res.value = new THREE.Vector2(W, H);
  composer.addPass(grade);
  const V = (a, d) => new THREE.Vector3(...(a || d));
  return {
    render(t, cfg, focusDist) {
      const c = merge(...cfg);
      if (bloom) { bloom.enabled = !!c.bloom; if (c.bloom) { bloom.strength = c.bloom.strength ?? 0.6; bloom.radius = c.bloom.radius ?? 0.5; bloom.threshold = c.bloom.threshold ?? 0.85; } }
      if (bokeh) { bokeh.enabled = !!c.dof; if (c.dof) { bokeh.uniforms.focus.value = focusDist ?? c.dof.focus ?? 10; bokeh.uniforms.aperture.value = c.dof.aperture ?? 0.0002; bokeh.uniforms.maxblur.value = c.dof.maxblur ?? 0.012; } }
      const g = c.grade || {}; const u = grade.uniforms;
      u.exposure.value = g.exposure ?? 1; u.contrast.value = g.contrast ?? 1; u.saturation.value = g.saturation ?? 1;
      u.tint.value = V(g.tint, [1, 1, 1]); u.lift.value = V(g.lift, [0, 0, 0]); u.gain.value = V(g.gain, [1, 1, 1]);
      u.grain.value = c.grain ?? 0; u.chroma.value = c.chroma ?? 0; u.uTime.value = t;
      composer.render();
    },
  };
}
