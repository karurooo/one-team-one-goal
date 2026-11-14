// PostToolUse hook: format and lint-fix the file Claude just edited.
// Never blocks: missing tools (prettier/eslint arrive with T-SETUP-05) or lint errors just pass through.
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const PRETTIER_EXT = /\.(ts|tsx|js|jsx|mjs|cjs|json|md|css|html)$/;
const ESLINT_EXT = /\.(ts|tsx|js|jsx|mjs|cjs)$/;

let filePath;
try {
  filePath = JSON.parse(readFileSync(0, 'utf8')).tool_input?.file_path;
} catch {
  process.exit(0);
}
if (!filePath) process.exit(0);

const root = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const rel = path.relative(root, path.resolve(filePath)).split(path.sep).join('/');
if (rel.startsWith('..') || rel.includes('node_modules/')) process.exit(0);

const run = (args, cwd) =>
  spawnSync('npx', ['--no-install', ...args], { cwd, stdio: 'ignore', shell: process.platform === 'win32' });

if (PRETTIER_EXT.test(rel)) run(['prettier', '--write', filePath], root);
// ESLint config currently lives only in frontend/.
if (ESLINT_EXT.test(rel) && rel.startsWith('frontend/'))
  run(['eslint', '--fix', filePath], path.join(root, 'frontend'));

process.exit(0);
