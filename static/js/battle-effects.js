const BattleEffects = (() => {
    const currentSpeed = { a: 50, b: 50 };
    const maxSpeed = { a: 100, b: 100 };

    function getDisc(side) {
        return document.getElementById(`spin-${side}`);
    }

    function setSpinSpeed(side, speed) {
        const disc = getDisc(side);
        if (!disc) return;
        const ratio = Math.max(speed, 5) / 100;
        const duration = Math.max(0.15, 1.2 - ratio * 1.0);
        disc.style.setProperty("--spin-duration", `${duration}s`);
    }

    function updateSpeedBar(side, current, max) {
        const bar = document.getElementById(`speed-bar-${side}`);
        const val = document.getElementById(`speed-val-${side}`);
        if (!max) return;
        const pct = Math.max(0, Math.min(100, (current / max) * 100));
        if (bar) {
            bar.style.width = `${pct}%`;
            if (pct > 50) bar.style.backgroundColor = "#818cf8";
            else if (pct > 25) bar.style.backgroundColor = "#fbbf24";
            else bar.style.backgroundColor = "#ef4444";
        }
        if (val) val.textContent = Math.round(current);
    }

    function createFloatingText(side, text, color) {
        const disc = getDisc(side);
        if (!disc) return;
        const parent = disc.parentElement;
        const el = document.createElement("div");
        el.className = "battle-float-text";
        el.textContent = text;
        el.style.color = color;
        parent.appendChild(el);
        setTimeout(() => el.remove(), 1000);
    }

    function createSparks(side, color, count) {
        const disc = getDisc(side);
        if (!disc) return;
        const parent = disc.parentElement;
        for (let i = 0; i < (count || 6); i++) {
            const spark = document.createElement("div");
            spark.className = "battle-spark";
            spark.style.background = color;
            const angle = Math.random() * Math.PI * 2;
            const dist = 30 + Math.random() * 40;
            spark.style.setProperty("--sx", `${Math.cos(angle) * dist}px`);
            spark.style.setProperty("--sy", `${Math.sin(angle) * dist}px`);
            spark.style.left = "50%";
            spark.style.top = "50%";
            parent.appendChild(spark);
            setTimeout(() => spark.remove(), 400);
        }
    }

    function createSlashOnDefender(defenderSide, crit) {
        const disc = getDisc(defenderSide);
        if (!disc) return;
        const parent = disc.parentElement;
        const slash = document.createElement("div");
        slash.className = crit ? "battle-slash battle-slash-crit" : "battle-slash";
        parent.appendChild(slash);
        setTimeout(() => slash.remove(), 400);
    }

    function removeTempClass(side, cls, duration) {
        setTimeout(() => {
            const disc = getDisc(side);
            if (disc) disc.classList.remove(cls);
        }, duration);
    }

    return {
        updateSpeed(side, speed, max) {
            currentSpeed[side] = speed;
            if (max) maxSpeed[side] = max;
            setSpinSpeed(side, speed);
            updateSpeedBar(side, speed, maxSpeed[side]);
        },
        accel(side, oldSpeed, newSpeed) {
            const disc = getDisc(side);
            if (!disc) return;
            disc.classList.add("spin-accel-glow");
            removeTempClass(side, "spin-accel-glow", 500);
            setSpinSpeed(side, newSpeed);
            createFloatingText(side, "가속!", "#fbbf24");
            createSparks(side, "#fbbf24", 5);
        },
        accelFail(side) {},
        firstStrike(side) {
            const disc = getDisc(side);
            if (!disc) return;
            createSparks(side, "#818cf8", 4);
        },
        attack(attackerSide, defenderSide, crit) {
            const atkDisc = getDisc(attackerSide);
            if (atkDisc) {
                atkDisc.classList.add("spin-attack-lunge");
                removeTempClass(attackerSide, "spin-attack-lunge", 350);
            }
            const defDisc = getDisc(defenderSide);
            if (defDisc) {
                setTimeout(() => {
                    defDisc.classList.add(crit ? "spin-crit-hit" : "spin-hit-wobble");
                    removeTempClass(defenderSide, crit ? "spin-crit-hit" : "spin-hit-wobble", crit ? 500 : 400);
                }, 120);
            }
            createSlashOnDefender(defenderSide, crit);
            createSparks(defenderSide, crit ? "#f97316" : "#ef4444", crit ? 10 : 5);
        },
        counterFail(side) {},
        eventPositive(side, floatText) {
            createFloatingText(side, floatText || "↑", "#34d399");
            createSparks(side, "#34d399", 4);
        },
        eventNegative(side, floatText) {
            createFloatingText(side, floatText || "↓", "#a78bfa");
        },
        endure(side) {
            const disc = getDisc(side);
            if (!disc) return;
            disc.classList.add("spin-endure-aura");
            removeTempClass(side, "spin-endure-aura", 800);
            createFloatingText(side, "인내!", "#fde68a");
            createSparks(side, "#fde68a", 8);
        },
        stop(side) {
            const disc = getDisc(side);
            if (!disc) return;
            disc.classList.add("stopped");
            disc.style.setProperty("--spin-duration", "0s");
        },
        stopBoth() {
            ["a", "b"].forEach((s) => this.stop(s));
        },
        decel(aOld, aNew, bOld, bNew, maxA, maxB) {
            updateSpeedBar("a", aNew, maxA);
            updateSpeedBar("b", bNew, maxB);
            setSpinSpeed("a", aNew);
            setSpinSpeed("b", bNew);
            currentSpeed.a = aNew;
            currentSpeed.b = bNew;
        },
        battleEnd(winner) {
            if (winner === "draw") return;
            const disc = getDisc(winner);
            if (!disc) return;
            disc.classList.add("spin-winner");
            createSparks(winner, "#fbbf24", 12);
        },
        reset() {
            ["a", "b"].forEach((side) => {
                const disc = getDisc(side);
                if (!disc) return;
                disc.classList.remove("stopped", "spin-winner", "spin-endure-aura", "spin-accel-glow", "spin-attack-lunge", "spin-hit-wobble", "spin-crit-hit");
            });
        },
    };
})();
