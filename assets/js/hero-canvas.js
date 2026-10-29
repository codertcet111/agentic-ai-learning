/** Animated neural mesh for the home hero — pure canvas, no assets. */
(function () {
  function init(canvas) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w = 0;
    let h = 0;
    const nodes = [];
    const count = reduced ? 24 : 48;

    function resize() {
      const rect = canvas.parentElement.getBoundingClientRect();
      w = canvas.width = Math.floor(rect.width * devicePixelRatio);
      h = canvas.height = Math.floor(rect.height * devicePixelRatio);
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    }

    function seed() {
      nodes.length = 0;
      const rw = canvas.parentElement.clientWidth;
      const rh = canvas.parentElement.clientHeight;
      for (let i = 0; i < count; i++) {
        nodes.push({
          x: Math.random() * rw,
          y: Math.random() * rh,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
        });
      }
    }

    function draw() {
      const rw = canvas.parentElement.clientWidth;
      const rh = canvas.parentElement.clientHeight;
      ctx.fillStyle = "#0a0e14";
      ctx.fillRect(0, 0, rw, rh);

      const grad = ctx.createRadialGradient(rw * 0.3, rh * 0.2, 0, rw * 0.5, rh * 0.5, rw * 0.8);
      grad.addColorStop(0, "rgba(94, 234, 212, 0.08)");
      grad.addColorStop(1, "transparent");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, rw, rh);

      for (const n of nodes) {
        if (!reduced) {
          n.x += n.vx;
          n.y += n.vy;
          if (n.x < 0 || n.x > rw) n.vx *= -1;
          if (n.y < 0 || n.y > rh) n.vy *= -1;
        }
      }

      const maxDist = 120;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy);
          if (d < maxDist) {
            const alpha = (1 - d / maxDist) * 0.35;
            ctx.strokeStyle = `rgba(94, 234, 212, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      for (const n of nodes) {
        ctx.fillStyle = "rgba(167, 139, 250, 0.9)";
        ctx.beginPath();
        ctx.arc(n.x, n.y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function loop() {
      draw();
      if (!reduced) requestAnimationFrame(loop);
    }

    resize();
    seed();
    loop();
    window.addEventListener("resize", () => {
      resize();
      seed();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    init(document.getElementById("hero-canvas"));
  });
})();
