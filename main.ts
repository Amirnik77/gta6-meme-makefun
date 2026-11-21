// Entry program for make.fun's "Post a GTA 6 meme on X" bounty (gta6-meme-x-01).
//
// The entry itself is a post on X: a GTA 6 meme picture with make.fun's ghost in
// it, posted from a public account with the bounty link, a @makefunai tag and our
// play code in the text. This program's whole job is to hand that post's address
// to the house: it reads POST.json from the repository root and writes the same
// bytes to POST.json in the output directory, where the gate picks it up.
//
// Contract kept deliberately small and safe:
//   - Node 22, standard library only, no network, no clock, no randomness.
//   - Deterministic: the output is a byte-for-byte copy of the input file, so
//     two runs over the same repository write identical bytes.
//   - Silent on success; a clear message on stderr and exit code 1 on failure.
//
// Where things live: inside the grader the repository is /bot and the output
// directory is /output. For a local run the kit stands them in with two
// environment variables:
//
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const POST_FILE = 'POST.json';

/** The directory the repository is mounted at (the bot dir). */
function botDir(): string {
  return process.env.MAKEFUN_BOT_DIR ?? '/bot';
}

/** The directory the house reads this entry's outputs from. */
function outputDir(): string {
  return process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
}

/** Stops the run with a readable reason. */
function fail(reason: string): never {
  console.error(`gta6-meme-x-01: ${reason}`);
  process.exit(1);
}

/**
 * Reads POST.json and checks it is shaped like the hand-in the gate expects:
 * one JSON object whose "url" names the post. The bytes themselves are what
 * get copied; this only guards against handing in a broken file.
 */
function readPostFile(dir: string): Buffer {
  const path = join(dir, POST_FILE);
  let bytes: Buffer;
  try {
    bytes = readFileSync(path);
  } catch {
    fail(`cannot read ${path}`);
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(bytes.toString('utf8'));
  } catch {
    fail(`${POST_FILE} is not valid JSON`);
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    fail(`${POST_FILE} must be a JSON object like {"url": "https://x.com/<handle>/status/<id>"}`);
  }
  const url = (parsed as { url?: unknown }).url;
  if (typeof url !== 'string' || url.length === 0) {
    fail(`${POST_FILE} must carry the post's address in its "url" field`);
  }
  return bytes;
}

function main(): void {
  const bytes = readPostFile(botDir());
  const target = join(outputDir(), POST_FILE);
  try {
    mkdirSync(outputDir(), { recursive: true });
    writeFileSync(target, bytes);
  } catch (err) {
    fail(`cannot write ${target}: ${(err as Error).message}`);
  }
  // Read the copy back and compare: the house grades what actually landed in
  // the output directory, so a short or torn write must fail here, loudly,
  // rather than hand the gate a POST.json that is not the one in the repo.
  let landed: Buffer;
  try {
    landed = readFileSync(target);
  } catch (err) {
    fail(`cannot read back ${target}: ${(err as Error).message}`);
  }
  if (!landed.equals(bytes)) {
    fail(`${target} does not match the repository's ${POST_FILE} byte for byte`);
  }
}

main();
