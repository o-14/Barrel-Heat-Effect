const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const meshDir = path.join(root, "Data", "Meshes", "GunHeatHaze");
const textureDir = path.join(root, "Data", "Textures", "Effects");
const gradientDir = path.join(textureDir, "Gradients");

const sourceNif = path.join(
  meshDir,
  "AssaultRifleHeatMuzzle.minigun-wrapper-before-muzfallback-20260622-0149.nif",
);
const targetNif = path.join(meshDir, "AssaultRifleHeatMuzzle.nif");

const texturePath = path.join(textureDir, "HeatWallTile_d.dds");
const gradientPath = path.join(gradientDir, "HeatSharpGrad.dds");

function makeDdsHeader(width, height) {
  const header = Buffer.alloc(128);
  header.write("DDS ", 0, "ascii");
  header.writeUInt32LE(124, 4);
  header.writeUInt32LE(0x0002100f, 8);
  header.writeUInt32LE(height, 12);
  header.writeUInt32LE(width, 16);
  header.writeUInt32LE(width * 4, 20);
  header.writeUInt32LE(0, 24);
  header.writeUInt32LE(1, 28);
  header.writeUInt32LE(32, 76);
  header.writeUInt32LE(0x00000041, 80);
  header.writeUInt32LE(0, 84);
  header.writeUInt32LE(32, 88);
  header.writeUInt32LE(0x00ff0000, 92);
  header.writeUInt32LE(0x0000ff00, 96);
  header.writeUInt32LE(0x000000ff, 100);
  header.writeUInt32LE(0xff000000, 104);
  header.writeUInt32LE(0x00001000, 108);
  return header;
}

function writeDds(filePath, width, height, pixelFn) {
  const pixels = Buffer.alloc(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const [r, g, b, a] = pixelFn(x, y, width, height);
      const offset = (y * width + x) * 4;
      pixels[offset] = b;
      pixels[offset + 1] = g;
      pixels[offset + 2] = r;
      pixels[offset + 3] = a;
    }
  }
  fs.writeFileSync(filePath, Buffer.concat([makeDdsHeader(width, height), pixels]));
}

function clampByte(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function heatTilePixel(x, y, width, height) {
  const u = (x + 0.5) / width;
  const v = (y + 0.5) / height;
  const dx = u - 0.5;
  const dy = v - 0.52;
  const radius = Math.sqrt(dx * dx * 0.8 + dy * dy * 1.9);
  const falloff = Math.max(0, 1 - radius * 2.2);
  const waveA = Math.sin((u * 5.0 + v * 2.2) * Math.PI * 2);
  const waveB = Math.sin((u * 1.7 - v * 7.0) * Math.PI * 2);
  const ripple = Math.max(0, waveA * 0.55 + waveB * 0.35 + 0.35);
  const alpha = clampByte(Math.pow(falloff, 2.0) * ripple * 42);
  const tone = clampByte(122 + ripple * 48);
  return [tone, tone + 4, tone + 8, alpha];
}

function heatGradientPixel(x, y, width, height) {
  const t = x / Math.max(1, width - 1);
  const alpha = Math.sin(t * Math.PI);
  const v = clampByte(96 + alpha * 50);
  return [v, v + 4, v + 8, clampByte(alpha * 64)];
}

function replaceAllSameLength(buffer, from, to) {
  const fromBytes = Buffer.from(from, "ascii");
  const toBytes = Buffer.from(to, "ascii");
  if (fromBytes.length !== toBytes.length) {
    throw new Error(`Replacement length mismatch: ${from} -> ${to}`);
  }

  let count = 0;
  let index = buffer.indexOf(fromBytes);
  while (index !== -1) {
    toBytes.copy(buffer, index);
    count += 1;
    index = buffer.indexOf(fromBytes, index + toBytes.length);
  }
  return count;
}

fs.mkdirSync(textureDir, { recursive: true });
fs.mkdirSync(gradientDir, { recursive: true });

writeDds(texturePath, 256, 256, heatTilePixel);
writeDds(gradientPath, 256, 1, heatGradientPixel);

const nif = Buffer.from(fs.readFileSync(sourceNif));
const replacements = [
  replaceAllSameLength(
    nif,
    "textures\\Effects\\FireWallTile_d.dds",
    "textures\\Effects\\HeatWallTile_d.dds",
  ),
  replaceAllSameLength(
    nif,
    "textures\\Effects\\Gradients\\FireSharpGrad.dds",
    "textures\\Effects\\Gradients\\HeatSharpGrad.dds",
  ),
];

if (replacements.some((count) => count === 0)) {
  throw new Error(`Missing expected texture path replacement: ${replacements.join(", ")}`);
}

fs.writeFileSync(targetNif, nif);
console.log(
  JSON.stringify(
    {
      targetNif,
      texturePath,
      gradientPath,
      replacements,
      targetBytes: fs.statSync(targetNif).size,
      textureBytes: fs.statSync(texturePath).size,
      gradientBytes: fs.statSync(gradientPath).size,
    },
    null,
    2,
  ),
);
