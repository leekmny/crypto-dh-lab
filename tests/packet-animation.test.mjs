import assert from 'node:assert/strict';
import { test } from 'node:test';
import { PacketAnimation } from '../web/animation.js';

function fixture(t, reducedMotion = false) {
  const frames = new Map();
  let nextFrame = 0;
  const label = { textContent: '' };
  const packet = {
    hidden: true,
    classList: {
      add() { packet.hidden = true; },
      remove() { packet.hidden = false; },
    },
    querySelector() { return label; },
    setAttribute(name, value) { packet[name] = value; },
  };
  const route = (start, direction) => ({
    getTotalLength: () => 600,
    getPointAtLength: distance => ({ x: start + direction * distance, y: 50 }),
  });
  const elements = { '#packet-animation': packet, '#route-a': route(100, 1), '#route-b': route(700, -1) };
  const svg = { dataset: {}, querySelector: selector => elements[selector] };
  const globals = {
    matchMedia: () => ({ matches: reducedMotion }),
    requestAnimationFrame(callback) {
      frames.set(++nextFrame, callback);
      return nextFrame;
    },
    cancelAnimationFrame(id) { frames.delete(id); },
  };
  for (const [name, value] of Object.entries(globals)) {
    const previous = Object.getOwnPropertyDescriptor(globalThis, name);
    Object.defineProperty(globalThis, name, { configurable: true, value });
    t.after(() => previous ? Object.defineProperty(globalThis, name, previous) : delete globalThis[name]);
  }
  function tick(now) {
    const callbacks = [...frames.values()];
    frames.clear();
    for (const callback of callbacks) callback(now);
  }
  return { animation: new PacketAnimation(svg), frames, label, packet, svg, tick };
}

test('recorded sends move labeled packets in either direction at playback speed', t => {
  const { animation, label, packet, svg, tick } = fixture(t);
  animation.transfer('Alice', 'DH 공개값');
  assert.equal(svg.dataset.sender, 'alice');
  assert.equal(label.textContent, 'DH 공개값');
  assert.equal(packet.transform, 'translate(100 50)');
  tick(0);
  tick(250);
  assert.equal(packet.transform, 'translate(193.75 50)');
  tick(500);
  assert.equal(packet.transform, 'translate(400 50)');
  tick(1000);
  assert.equal(packet.transform, 'translate(700 50)');
  assert.equal(packet.hidden, false);

  animation.transfer('Bob', '키 확인', 2);
  assert.equal(svg.dataset.sender, 'bob');
  assert.equal(label.textContent, '키 확인');
  assert.equal(packet.transform, 'translate(700 50)');
  tick(1000);
  tick(1500);
  assert.equal(packet.transform, 'translate(100 50)');
});

test('reduced motion shows a stationary packet with direction and type', t => {
  const { animation, frames, label, packet, svg } = fixture(t, true);
  animation.transfer('Bob', '응용 메시지');
  assert.equal(svg.dataset.sender, 'bob');
  assert.equal(label.textContent, '응용 메시지');
  assert.equal(packet.hidden, false);
  assert.equal(packet.transform, 'translate(400 50)');
  assert.equal(frames.size, 0);
});

test('stopping clears the route, packet and pending animation frame', t => {
  const { animation, frames, packet, svg } = fixture(t);
  animation.transfer('Alice', 'DH 공개값');
  assert.equal(frames.size, 1);
  animation.stop();
  assert.equal(packet.hidden, true);
  assert.equal(svg.dataset.sender, undefined);
  assert.equal(frames.size, 0);
});
