const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const sourceNif = path.join(root, "$out", "Meshes", "Effects", "FlameThrowerProjectileSprayVaporizer01.nif");
const meshDir = path.join(root, "Data", "Meshes", "GunHeatHaze");
const textureDir = path.join(root, "Data", "Textures", "Effects", "Gradients");
const targetNif = path.join(meshDir, "FlameThrowerHeatRefractionNoFlame.nif");
const targetGradient = path.join(textureDir, "HeatNoFlamesGrad01.dds");
const targetDiffuse = path.join(root, "Data", "Textures", "Effects", "HeatClearVapor01.dds");

const vanillaGradientPath = "textures\\Effects\\Gradients\\FlameThrowerGrad01.dds";
const noFlameGradientPath = "textures\\Effects\\Gradients\\HeatNoFlamesGrad01.dds";
const vanillaDiffusePath = "textures\\Effects\\SmokeVapor01Tile.dds";
const noFlameDiffusePath = "textures\\Effects\\HeatClearVapor01.dds";

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

function writeTransparentDds(filePath, width, height) {
  const pixels = Buffer.alloc(width * height * 4, 0);
  fs.writeFileSync(filePath, Buffer.concat([makeDdsHeader(width, height), pixels]));
}

function replaceAllSameLength(buffer, from, to) {
  const fromBytes = Buffer.from(from, "ascii");
  const toBytes = Buffer.from(to, "ascii");
  if (fromBytes.length !== toBytes.length) {
    throw new Error(`Replacement length mismatch: ${fromBytes.length} -> ${toBytes.length}`);
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

fs.mkdirSync(meshDir, { recursive: true });
fs.mkdirSync(textureDir, { recursive: true });
fs.mkdirSync(path.dirname(targetDiffuse), { recursive: true });

const nif = Buffer.from(fs.readFileSync(sourceNif));
const gradientReplacements = replaceAllSameLength(nif, vanillaGradientPath, noFlameGradientPath);
const diffuseReplacements = replaceAllSameLength(nif, vanillaDiffusePath, noFlameDiffusePath);
if (gradientReplacements === 0) {
  throw new Error(`Could not find ${vanillaGradientPath} in ${sourceNif}`);
}
if (diffuseReplacements === 0) {
  throw new Error(`Could not find ${vanillaDiffusePath} in ${sourceNif}`);
}

writeTransparentDds(targetGradient, 256, 1);
writeTransparentDds(targetDiffuse, 256, 256);
fs.writeFileSync(targetNif, nif);

console.log(
  JSON.stringify(
    {
      sourceNif,
      targetNif,
      targetGradient,
      targetDiffuse,
      gradientReplacements,
      diffuseReplacements,
      targetNifBytes: fs.statSync(targetNif).size,
      targetGradientBytes: fs.statSync(targetGradient).size,
      targetDiffuseBytes: fs.statSync(targetDiffuse).size,
    },
    null,
    2,
  ),
);
