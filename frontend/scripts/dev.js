#!/usr/bin/env node
const { existsSync } = require('node:fs');
const { spawn } = require('node:child_process');
const path = require('node:path');

const cwd = process.cwd();
const nodeModules = path.join(cwd, 'node_modules');

function hasModule(name) {
  try {
    require.resolve(name, { paths: [cwd] });
    return true;
  } catch (_) {
    return false;
  }
}

/**
 * Runs a command and pipes stdio. Resolves when the process exits.
 */
function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: 'inherit', shell: process.platform === 'win32', ...opts });
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} exited with code ${code}`));
    });
  });
}

async function main() {
  const needsInstall =
    !existsSync(nodeModules) ||
    !hasModule('@tailwindcss/postcss') ||
    !hasModule('tailwindcss') ||
    !hasModule('postcss');
  try {
    if (needsInstall) {
      const hasLock = existsSync(path.join(cwd, 'package-lock.json'));
      console.log(`📦 Dependencies not found. Running ${hasLock ? 'npm ci' : 'npm install'}...`);
      try {
        await run('npm', [hasLock ? 'ci' : 'install']);
      } catch (e) {
        console.warn('⚠️ npm ci failed, falling back to npm install');
        await run('npm', ['install']);
      }
    } else {
      console.log('✅ Dependencies present. Skipping install.');
    }
    console.log('🚀 Starting dev server...');
    await run('npm', ['run', 'dev']);
  } catch (err) {
    console.error('❌ Failed to start UI:', err?.message || err);
    process.exit(1);
  }
}

main();
