#!/usr/bin/env node

/**
 * PWA Icon Generator Script
 *
 * This script generates PWA icons from the base SVG icon.
 *
 * Usage: node scripts/generate-icons.js
 *
 * Requirements: sharp (npm install sharp --save-dev)
 */

const fs = require('fs');
const path = require('path');

async function generateIcons() {
  let sharp;
  try {
    sharp = require('sharp');
  } catch {
    console.log('Sharp not installed. Installing...');
    const { execSync } = require('child_process');
    execSync('npm install sharp --save-dev', { stdio: 'inherit' });
    sharp = require('sharp');
  }

  const iconsDir = path.join(__dirname, '../public/icons');
  const svgPath = path.join(iconsDir, 'icon.svg');

  if (!fs.existsSync(svgPath)) {
    console.error('icon.svg not found in public/icons/');
    process.exit(1);
  }

  const sizes = [
    { name: 'icon-72x72.png', size: 72 },
    { name: 'icon-96x96.png', size: 96 },
    { name: 'icon-128x128.png', size: 128 },
    { name: 'icon-144x144.png', size: 144 },
    { name: 'icon-152x152.png', size: 152 },
    { name: 'icon-192x192.png', size: 192 },
    { name: 'icon-384x384.png', size: 384 },
    { name: 'icon-512x512.png', size: 512 },
    { name: 'apple-touch-icon.png', size: 180 },
    { name: 'badge-72x72.png', size: 72 },
    { name: 'shortcut-picks.png', size: 96 },
    { name: 'shortcut-matches.png', size: 96 },
  ];

  console.log('Generating PWA icons...\n');

  for (const { name, size } of sizes) {
    const outputPath = path.join(iconsDir, name);
    await sharp(svgPath)
      .resize(size, size)
      .png()
      .toFile(outputPath);
    console.log(`  ✓ ${name} (${size}x${size})`);
  }

  console.log('\n✅ All icons generated successfully!');
  console.log(`   Location: ${iconsDir}`);
}

generateIcons().catch(console.error);
