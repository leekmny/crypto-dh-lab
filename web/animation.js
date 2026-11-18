// 이 모듈은 전달받은 실제 송신 이벤트를 시각화할 뿐, 암호 연산이나 결과를 만들지 않는다.
export class PacketAnimation {
  constructor(svg) {
    this.packet = svg.querySelector('#packet-animation');
    this.paths = { Alice: svg.querySelector('#route-a'), Bob: svg.querySelector('#route-b') };
    this.frame = null;
  }
  stop() {
    cancelAnimationFrame(this.frame);
    this.packet.classList.add('hidden');
  }
  transfer(sender, speed = 1) {
    this.stop();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const path = this.paths[sender];
    if (!path) return;
    const length = path.getTotalLength();
    const start = performance.now();
    const duration = 1000 / speed;
    this.packet.classList.remove('hidden');
    const draw = now => {
      const progress = Math.min(1, (now - start) / duration);
      const point = path.getPointAtLength(length * progress);
      this.packet.setAttribute('transform', `translate(${point.x} ${point.y})`);
      if (progress < 1) this.frame = requestAnimationFrame(draw);
      else this.packet.classList.add('hidden');
    };
    this.frame = requestAnimationFrame(draw);
  }
}
