#!/usr/bin/env node
const { spawnSync } = require('child_process');
const path = require('path');

// Find python3 or python
const python = process.platform === 'win32' ? 'python' : 'python3';
const args = ['-m', 'datamorph.cli', ...process.argv.slice(2)];
const result = spawnSync(python, args, { stdio: 'inherit' });
process.exit(result.status != null ? result.status : 1);
