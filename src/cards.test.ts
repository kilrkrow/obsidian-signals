import { strict as assert } from "node:assert";
import { test } from "node:test";
// Node runs this file with type stripping, which needs the explicit .ts extension.
// @ts-expect-error TS5097: the plugin build never imports this test file.
import { cardFromNote, parseFrontmatter, pillLabel, sortCards, youtubeIdFromDrop } from "./cards.ts";

test("parses quoted youtube titles", () => {
  const text = `---
type: youtube
id: s9sb4WhVcw4
title: "God is saying, \\"Stop asking for so much confirmation\\""
author: Edgar Sandoval Jr
collection_status: ok
collected_at: "2026-10-23T11:58:52Z"
---
# body
`;
  const meta = parseFrontmatter(text);
  assert.equal(meta.title, 'God is saying, "Stop asking for so much confirmation"');
  assert.equal(meta.collection_status, "ok");
});

test("card sorts newest first", () => {
  const older = cardFromNote("Machine/Reference/YouTube/a.md", "---\nid: aaaaaaaaaaa\ntitle: Older\ncollected_at: \"2026-10-01T00:00:00Z\"\n---\n");
  const newer = cardFromNote("Machine/Reference/YouTube/b.md", "---\nid: bbbbbbbbbbb\ntitle: Newer\ncollected_at: \"2026-10-23T00:00:00Z\"\n---\n");
  assert.deepEqual(sortCards([older, newer]).map((card) => card.id), ["bbbbbbbbbbb", "aaaaaaaaaaa"]);
});

test("reads a video id from a thumbnail drop", () => {
  const html = '<img src="https://i.ytimg.com/vi/4z2i6UsQG1k/hqdefault.jpg">';
  assert.equal(youtubeIdFromDrop(html), "4z2i6UsQG1k");
  assert.equal(youtubeIdFromDrop("https://youtu.be/S2eESu4hSKk"), "S2eESu4hSKk");
  assert.equal(pillLabel("ok"), "captured");
  assert.equal(pillLabel("partial"), "partial");
});
