// Held items: a 16x16 item sprite extruded into a 1-pixel-thick 3D model, the way the game draws swords, tools and sticks
// in a hand. Front and back are the sprite; every opaque pixel on an outline gets a 1x1 side face coloured by that pixel.
// Item names resolve: project items/ folder -> original textures in work/vanilla/items -> CC0 sprites in core/builtin/items.

export function extrudeItem(THREE, img, tex, size = 0.85) {
  const W = img.width, H = img.height; const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0); const d = g.getImageData(0, 0, W, H).data;
  const op = (x, y) => x >= 0 && y >= 0 && x < W && y < H && d[(y * W + x) * 4 + 3] > 127;
  const px = size / W, th = size / 16; // one sprite pixel; thickness = one 16th of the item, like the game
  const pos = [], nor = [], uv = [], idx = [];
  const quad = (ps, n, uvs) => { const b = pos.length / 3; ps.forEach((p, i) => { pos.push(...p); nor.push(...n); uv.push(...uvs[i]); }); idx.push(b, b + 1, b + 2, b, b + 2, b + 3); };
  const X = (x) => (x - W / 2) * px, Y = (y) => (H / 2 - y) * px, z0 = -th / 2, z1 = th / 2;
  // front (+z) and back (-z): the whole sprite (alpha test drops the empty pixels)
  quad([[X(0), Y(H), z1], [X(W), Y(H), z1], [X(W), Y(0), z1], [X(0), Y(0), z1]], [0, 0, 1], [[0, 0], [1, 0], [1, 1], [0, 1]]);
  quad([[X(W), Y(H), z0], [X(0), Y(H), z0], [X(0), Y(0), z0], [X(W), Y(0), z0]], [0, 0, -1], [[1, 0], [0, 0], [0, 1], [1, 1]]);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (!op(x, y)) continue;
    const u0 = (x + 0.25) / W, u1 = (x + 0.75) / W, v0 = 1 - (y + 0.75) / H, v1 = 1 - (y + 0.25) / H; const U = [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
    if (!op(x - 1, y)) quad([[X(x), Y(y + 1), z0], [X(x), Y(y + 1), z1], [X(x), Y(y), z1], [X(x), Y(y), z0]], [-1, 0, 0], U);
    if (!op(x + 1, y)) quad([[X(x + 1), Y(y + 1), z1], [X(x + 1), Y(y + 1), z0], [X(x + 1), Y(y), z0], [X(x + 1), Y(y), z1]], [1, 0, 0], U);
    if (!op(x, y - 1)) quad([[X(x), Y(y), z1], [X(x + 1), Y(y), z1], [X(x + 1), Y(y), z0], [X(x), Y(y), z0]], [0, 1, 0], U);
    if (!op(x, y + 1)) quad([[X(x), Y(y + 1), z0], [X(x + 1), Y(y + 1), z0], [X(x + 1), Y(y + 1), z1], [X(x), Y(y + 1), z1]], [0, -1, 0], U);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); geo.setIndex(idx); geo.computeBoundingSphere();
  const mat = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, side: THREE.FrontSide });
  const mesh = new THREE.Mesh(geo, mat); mesh.castShadow = true;
  return { mesh, mat, px };
}

// Mount an item in a hand. `arm` is the arm group (pivot at the shoulder; the hand is 10 px below it).
// Sprites are drawn grip-bottom-left / tip-top-right, so the sprite's diagonal becomes the blade: it points forward and up
// out of the fist, flat side facing out, like the third-person view in the game.
export function mountItem(THREE, arm, item, opts = {}) {
  const PX = 1 / 16; const hold = new THREE.Group();
  hold.position.set(0, -10 * PX, (opts.forward ?? 1) * PX); arm.add(hold);
  const grip = new THREE.Group(); hold.add(grip);
  grip.rotation.set(opts.tilt ?? 0.15, -Math.PI / 2 * (opts.left ? -1 : 1), 0);
  const m = item.mesh; const s = item.px; // the grip pixel (about 3,12 of 16) sits in the fist
  m.position.set((8 - 3.5) * s, (12.5 - 8) * s, 0);
  grip.add(m);
  return hold;
}
