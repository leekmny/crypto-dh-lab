// 이 모듈은 전달받은 실제 송신 이벤트를 시각화할 뿐, 암호 연산이나 결과를 만들지 않는다.
export class PacketAnimation {
  constructor(svg) {
    this.svg = svg;
    this.packet = svg.querySelector('#packet-animation');
    this.label = this.packet.querySelector('text');
    this.paths = { Alice: svg.querySelector('#route-a'), Bob: svg.querySelector('#route-b') };
    this.motion = matchMedia('(prefers-reduced-motion: reduce)');
    this.frame = null;
  }

  stop() {
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    this.packet.classList.add('hidden');
    delete this.svg.dataset.sender;
  }

  transfer(sender, label, speed = 1) {
    this.stop();
    const path = this.paths[sender];
    if (!path) return;
    const length = path.getTotalLength();
    const place = progress => {
      const point = path.getPointAtLength(length * progress);
      this.packet.setAttribute('transform', `translate(${point.x} ${point.y})`);
    };
    this.svg.dataset.sender = sender.toLowerCase();
    this.label.textContent = label;
    place(this.motion.matches ? 0.5 : 0);
    this.packet.classList.remove('hidden');
    if (this.motion.matches) return;

    let start;
    const duration = 1000 / speed;
    const draw = now => {
      start ??= now;
      const progress = Math.min(1, (now - start) / duration);
      place(progress * progress * (3 - 2 * progress));
      this.frame = progress < 1 ? requestAnimationFrame(draw) : null;
    };
    this.frame = requestAnimationFrame(draw);
  }
}
