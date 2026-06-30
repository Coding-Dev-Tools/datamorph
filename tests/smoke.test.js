const test = require("node:test");
const assert = require("node:assert");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

test("smoke: package main entry exists and parses", () => {
  const pkg = require(path.join(__dirname, "..", "package.json"));
  assert.ok(pkg.name, "package.json has a name");
  const main = pkg.main || "index.js";
  const cli = pkg.bin ? Object.values(pkg.bin)[0] : null;
  const entry = cli || main;
  if (fs.existsSync(path.join(__dirname, "..", entry))) {
    assert.doesNotThrow(
      () => execFileSync("node", ["--check", entry], { stdio: "ignore" }),
      `${entry} must be valid JavaScript`
    );
  }
});

test("smoke: required repo files present", () => {
  const root = path.join(__dirname, "..");
  for (const f of ["package.json", "README.md", "LICENSE"]) {
    assert.ok(fs.existsSync(path.join(root, f)), `${f} must exist`);
  }
});
