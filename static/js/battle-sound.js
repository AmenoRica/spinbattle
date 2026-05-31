const BattleSound = (() => {
    let ctx = null;
    let enabled = localStorage.getItem("battleSound") === "on";

    function getCtx() {
        if (!ctx) {
            ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (ctx.state === "suspended") {
            ctx.resume();
        }
        return ctx;
    }

    function playTone(freq, duration, type, volume, ramp) {
        if (!enabled) return;
        const c = getCtx();
        const osc = c.createOscillator();
        const gain = c.createGain();
        osc.type = type || "sine";
        osc.frequency.value = freq;
        gain.gain.value = volume || 0.15;
        if (ramp) {
            osc.frequency.linearRampToValueAtTime(ramp, c.currentTime + duration);
        }
        gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
        osc.connect(gain);
        gain.connect(c.destination);
        osc.start(c.currentTime);
        osc.stop(c.currentTime + duration);
    }

    function playNoise(duration, volume) {
        if (!enabled) return;
        const c = getCtx();
        const bufferSize = c.sampleRate * duration;
        const buffer = c.createBuffer(1, bufferSize, c.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / bufferSize, 3);
        }
        const src = c.createBufferSource();
        src.buffer = buffer;
        const gain = c.createGain();
        gain.gain.value = volume || 0.12;
        src.connect(gain);
        gain.connect(c.destination);
        src.start(c.currentTime);
    }

    function playChord(freqs, duration, type, volume) {
        freqs.forEach((f, i) => {
            setTimeout(() => playTone(f, duration, type, volume), i * 60);
        });
    }

    return {
init() {
        const btn = document.getElementById("btn-sound");
        if (btn) btn.textContent = enabled ? "🔊" : "🔇";
    },
    toggle() {
        enabled = !enabled;
        localStorage.setItem("battleSound", enabled ? "on" : "off");
        if (enabled) getCtx();
        return enabled;
        },
        isEnabled() {
            return enabled;
        },
        accel() {
            playTone(400, 0.15, "sine", 0.12, 800);
        },
        accelFail() {
            playTone(300, 0.1, "triangle", 0.08, 200);
        },
        attack() {
            playNoise(0.12, 0.15);
            playTone(150, 0.08, "square", 0.06);
        },
        crit() {
            playNoise(0.2, 0.2);
            playTone(200, 0.15, "sawtooth", 0.1, 600);
        },
        eventPositive() {
            playChord([523, 659, 784], 0.2, "sine", 0.1);
        },
        eventNegative() {
            playChord([400, 350, 300], 0.25, "triangle", 0.1);
        },
        endure() {
            playTone(300, 0.3, "sine", 0.12, 900);
            setTimeout(() => playTone(600, 0.2, "sine", 0.1), 150);
        },
        stop() {
            playTone(500, 0.3, "sine", 0.1, 100);
        },
        stopBoth() {
            playTone(400, 0.4, "sine", 0.1, 80);
            setTimeout(() => playTone(350, 0.4, "sine", 0.1, 70), 100);
        },
        battleEnd(winner) {
            if (winner === "draw") {
                playChord([440, 440, 440], 0.3, "triangle", 0.08);
            } else {
                playChord([523, 659, 784, 1047], 0.3, "sine", 0.12);
            }
        },
        decel() {
            playTone(250, 0.15, "triangle", 0.06, 180);
        },
        firstStrike() {
            playTone(600, 0.08, "square", 0.08);
        },
        countdownBeep() {
            playTone(660, 0.15, "sine", 0.15);
        },
        countdownGo() {
            playTone(880, 0.12, "sine", 0.15, 1320);
            playTone(1320, 0.3, "sine", 0.12);
        },
    };
})();
