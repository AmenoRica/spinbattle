const BattleReplay = (() => {
    let logData = [];
    let currentIndex = 0;
    let timer = null;
    let playing = false;
    let speed = 1;
    let battleWeather = null;
    let battleCity = null;
    let battleWeatherName = null;
    let battleWeatherIcon = null;
    const BASE_INTERVAL = 600;

    function getInterval() {
        return BASE_INTERVAL / speed;
    }

    function getLogEl() {
        return document.getElementById("battle-log");
    }

    function addLogLine(text) {
        const el = getLogEl();
        if (!el) return;
        const p = document.createElement("p");
        p.textContent = text;
        p.className = "battle-log-line";
        el.appendChild(p);
        el.scrollTop = el.scrollHeight;
    }

    function getSideData(side) {
        const el = document.getElementById(`spin-${side}`);
        if (!el) return null;
        return {
            maxSpeed: parseFloat(el.dataset.maxSpeed) || 100,
        };
    }

    function processEntry(entry) {
        if (!entry) return;
        if (entry.text) {
            entry.text.split("\n").forEach((line) => addLogLine(line));
        }
        if (!entry.effects) return;

        const maxA = getSideData("a")?.maxSpeed || 200;
        const maxB = getSideData("b")?.maxSpeed || 200;

        entry.effects.forEach((fx) => {
            switch (fx.type) {
                case "battle_start":
                    break;
                case "turn_start":
                    break;
                case "accel":
                    BattleEffects.accel(fx.target, fx.old_speed, fx.new_speed);
                    BattleEffects.updateSpeed(fx.target, fx.new_speed, fx.target === "a" ? maxA : maxB);
                    BattleSound.accel();
                    break;
                case "accel_fail":
                    BattleEffects.accelFail(fx.target);
                    BattleSound.accelFail();
                    break;
                case "first_strike":
                    BattleEffects.firstStrike(fx.target);
                    BattleSound.firstStrike();
                    break;
                case "attack":
                    BattleEffects.attack(fx.attacker, fx.defender, fx.crit);
                    if (fx.crit) {
                        BattleSound.crit();
                    } else {
                        BattleSound.attack();
                    }
                    break;
                case "counter_fail":
                    BattleEffects.counterFail(fx.target);
                    break;
                case "event_positive":
                    BattleEffects.eventPositive(fx.target, fx.float_text);
                    BattleSound.eventPositive();
                    break;
                case "event_negative":
                    BattleEffects.eventNegative(fx.target, fx.float_text);
                    BattleSound.eventNegative();
                    break;
                case "weather_announce":
                    BattleEffects.startWeatherEffect(fx.weather);
                    break;
                case "weather_effect":
                    if (fx.stat === "attack" || fx.stat === "defense" || fx.stat === "luck" || fx.stat === "crit") {
                        BattleEffects.eventPositive(fx.target, "↑");
                    } else if (fx.stat === "decel") {
                        BattleEffects.eventNegative(fx.target, "↓");
                    } else if (fx.stat === "speed_recover") {
                        BattleEffects.eventPositive(fx.target, "↑");
                    }
                    break;
                case "weather_event":
                    if (fx.event_name === "rain_influx") {
                        BattleEffects.eventPositive(fx.target, fx.float_text || "🌧️");
                    } else if (fx.event_name === "snowstorm") {
                        BattleEffects.eventNegative(fx.target, fx.float_text || "❄️");
                    }
                    break;
                case "endure":
                    BattleEffects.endure(fx.target);
                    BattleSound.endure();
                    BattleEffects.updateSpeed(fx.target, fx.new_speed, fx.target === "a" ? maxA : maxB);
                    break;
                case "stop":
                    BattleEffects.stop(fx.target);
                    BattleSound.stop();
                    break;
                case "stop_both":
                    BattleEffects.stopBoth();
                    BattleSound.stopBoth();
                    break;
                case "decel":
                    BattleEffects.decel(fx.a_old, fx.a_new, fx.b_old, fx.b_new, maxA, maxB);
                    BattleSound.decel();
                    break;
                case "battle_end":
                    BattleEffects.battleEnd(fx.winner);
                    BattleSound.battleEnd(fx.winner);
                    pause();
                    showEndControls();
                    break;
            }
        });
    }

    function step() {
        if (currentIndex >= logData.length) {
            pause();
            return;
        }
        processEntry(logData[currentIndex]);
        currentIndex++;
    }

    function play() {
        if (playing) return;
        if (currentIndex >= logData.length) return;
        playing = true;
        updatePlayButton();
        timer = setInterval(() => {
            step();
            if (currentIndex >= logData.length) {
                pause();
            }
        }, getInterval());
    }

    function pause() {
        playing = false;
        if (timer) clearInterval(timer);
        timer = null;
        updatePlayButton();
    }

    function skip() {
        pause();
        while (currentIndex < logData.length) {
            processEntry(logData[currentIndex]);
            currentIndex++;
        }
    }

    function restart() {
        pause();
        currentIndex = 0;
        const el = getLogEl();
        if (el) el.innerHTML = "";
        BattleEffects.reset();
        hideEndControls();

        document.getElementById("spin-a").classList.add("stopped");
        document.getElementById("spin-b").classList.add("stopped");
        BattleEffects.updateSpeed("a", 0, 200);
        BattleEffects.updateSpeed("b", 0, 200);

        showCountdown(() => {
            initSpeedBars();
            play();
        });
    }

    function setSpeed(s) {
        speed = s;
        updateSpeedButtons();
        if (playing) {
            clearInterval(timer);
            timer = setInterval(step, getInterval());
        }
    }

    function initSpeedBars() {
        const elA = document.getElementById("spin-a");
        const elB = document.getElementById("spin-b");
        if (elA) {
            const s = parseFloat(elA.dataset.initSpeed);
            const m = parseFloat(elA.dataset.maxSpeed);
            BattleEffects.updateSpeed("a", s, m);
        }
        if (elB) {
            const s = parseFloat(elB.dataset.initSpeed);
            const m = parseFloat(elB.dataset.maxSpeed);
            BattleEffects.updateSpeed("b", s, m);
        }
    }

    function updatePlayButton() {
        const btn = document.getElementById("btn-play");
        if (!btn) return;
        btn.textContent = playing ? "⏸" : "▶";
    }

    function updateSpeedButtons() {
        document.querySelectorAll(".btn-speed").forEach((btn) => {
            const s = parseFloat(btn.dataset.speed);
            btn.classList.toggle("bg-indigo-600", s === speed);
            btn.classList.toggle("text-white", s === speed);
            btn.classList.toggle("bg-gray-700", s !== speed);
            btn.classList.toggle("text-gray-400", s !== speed);
        });
    }

    function showEndControls() {
        const el = document.getElementById("end-controls");
        if (el) el.classList.remove("hidden");

        const data = JSON.parse(localStorage.getItem("battle_data") || "null");
        if (data && data.mode === "ranked") {
            showScoreChanges(data);
        }
    }

    function showScoreChanges(data) {
        const diffA = data.spin_a.new_score - data.spin_a.old_score;
        const diffB = data.spin_b.new_score - data.spin_b.old_score;

        const scoreA = document.getElementById("spin-a-score");
        const scoreB = document.getElementById("spin-b-score");

        if (scoreA) {
            const sign = diffA >= 0 ? "+" : "";
            scoreA.textContent = `${data.spin_a.old_score} → ${data.spin_a.new_score} (${sign}${diffA})`;
            scoreA.style.color = diffA >= 0 ? "#4ade80" : "#f87171";
        }
        if (scoreB) {
            const sign = diffB >= 0 ? "+" : "";
            scoreB.textContent = `${data.spin_b.old_score} → ${data.spin_b.new_score} (${sign}${diffB})`;
            scoreB.style.color = diffB >= 0 ? "#4ade80" : "#f87171";
        }
    }

    function hideEndControls() {
        const el = document.getElementById("end-controls");
        if (el) el.classList.add("hidden");
    }

    function showCountdown(callback) {
        const overlay = document.getElementById("countdown-overlay");
        const textEl = document.getElementById("countdown-text");
        if (!overlay || !textEl) { callback(); return; }

        document.getElementById("spin-a").classList.add("stopped");
        document.getElementById("spin-b").classList.add("stopped");

        const steps = [];
        if (battleCity) steps.push(battleCity);
        if (battleWeatherName) steps.push((battleWeatherIcon || "") + " " + battleWeatherName);
        steps.push("3", "2", "1", BattleI18n.countdownGo);
        let i = 0;

        overlay.classList.remove("hidden");

        function next() {
            if (i >= steps.length) {
                overlay.classList.add("hidden");
                document.getElementById("spin-a").classList.remove("stopped");
                document.getElementById("spin-b").classList.remove("stopped");
                callback();
                return;
            }
            textEl.textContent = steps[i];
            textEl.classList.remove("animate-countdown-pulse");
            void textEl.offsetWidth;
            textEl.classList.add("animate-countdown-pulse");
            const isGo = steps[i] === BattleI18n.countdownGo;
            const isCount = steps[i] === "3" || steps[i] === "2" || steps[i] === "1";
            if (isCount) {
                BattleSound.countdownBeep();
            } else if (isGo) {
                BattleSound.countdownGo();
            }
            i++;
            setTimeout(next, 900);
        }
        next();
    }

    return {
        init(data) {
            logData = data.log || data;
            currentIndex = 0;
            speed = 1;
            battleWeather = data.weather || null;
            battleCity = data.city || null;
            battleWeatherName = data.weather_name || null;
            battleWeatherIcon = data.weather_icon || null;
            updateSpeedButtons();
            hideEndControls();
            BattleEffects.updateSpeed("a", 0, 200);
            BattleEffects.updateSpeed("b", 0, 200);
            showCountdown(() => {
                initSpeedBars();
                play();
            });
        },
        play,
        pause,
        skip,
        restart,
        setSpeed,
        toggleSound() {
            const on = BattleSound.toggle();
            const btn = document.getElementById("btn-sound");
            if (btn) btn.textContent = on ? "🔊" : "🔇";
        },
    };
})();

document.addEventListener("DOMContentLoaded", () => {
    const data = JSON.parse(localStorage.getItem("battle_data") || "null");
    if (!data) {
        document.getElementById("battle-log").innerHTML = '<p class="text-gray-500">' + BattleI18n.noBattleData + '</p>';
        return;
    }

    document.getElementById("spin-a-name").textContent = data.spin_a.name;
    document.getElementById("spin-a-img").src = data.spin_a.image_url;
    document.getElementById("spin-b-name").textContent = data.spin_b.name;
    document.getElementById("spin-b-img").src = data.spin_b.image_url;

    if (data.spin_a.spin_type_color) {
        const discA = document.getElementById("spin-a");
        discA.style.borderColor = data.spin_a.spin_type_color;
    }
    if (data.spin_b.spin_type_color) {
        const discB = document.getElementById("spin-b");
        discB.style.borderColor = data.spin_b.spin_type_color;
    }
    const typeA = document.getElementById("spin-a-type");
    const typeB = document.getElementById("spin-b-type");
    if (typeA && data.spin_a.spin_type_name) {
        typeA.textContent = data.spin_a.spin_type_name;
        typeA.style.color = data.spin_a.spin_type_color;
    }
    if (typeB && data.spin_b.spin_type_name) {
        typeB.textContent = data.spin_b.spin_type_name;
        typeB.style.color = data.spin_b.spin_type_color;
    }

    const initSpeedA = data.log[0]?.effects?.[0]?.stats_a?.speed || 50;
    const initSpeedB = data.log[0]?.effects?.[0]?.stats_b?.speed || 50;
    document.getElementById("spin-a").dataset.initSpeed = initSpeedA;
    document.getElementById("spin-a").dataset.maxSpeed = initSpeedA * 2;
    document.getElementById("spin-b").dataset.initSpeed = initSpeedB;
    document.getElementById("spin-b").dataset.maxSpeed = initSpeedB * 2;

    BattleSound.init();
    BattleReplay.init(data);

    const modeLabel = document.getElementById("battle-mode-label");
    if (modeLabel) {
        modeLabel.textContent = data.mode === "ranked" ? BattleI18n.rankedBattle : BattleI18n.friendlyBattle;
    }

    if (data.mode === "ranked") {
        const scoreA = document.getElementById("spin-a-score");
        const scoreB = document.getElementById("spin-b-score");
        if (scoreA) {
            scoreA.textContent = `${data.spin_a.old_score}${BattleI18n.pts}`;
            scoreA.style.color = "#9ca3af";
            scoreA.classList.remove("hidden");
        }
        if (scoreB) {
            scoreB.textContent = `${data.spin_b.old_score}${BattleI18n.pts}`;
            scoreB.style.color = "#9ca3af";
            scoreB.classList.remove("hidden");
        }
    }

    if (data.weather) {
        const weatherInfo = document.getElementById("weather-info");
        const weatherIcon = document.getElementById("weather-icon");
        const weatherCity = document.getElementById("weather-city");
        if (weatherInfo && weatherIcon && weatherCity) {
            weatherInfo.classList.remove("hidden");
            weatherInfo.classList.add("weather-" + data.weather);
            weatherIcon.textContent = data.weather_icon || "";
            weatherCity.textContent = (data.city || "") + " " + (data.weather_name || "");
        }
        BattleEffects.startWeatherEffect(data.weather);
    }

    document.getElementById("btn-play").addEventListener("click", () => {
        const el = document.getElementById("btn-play");
        if (el.textContent === "▶") BattleReplay.play();
        else BattleReplay.pause();
    });
    document.getElementById("btn-restart").addEventListener("click", () => BattleReplay.restart());
    document.getElementById("btn-skip").addEventListener("click", () => BattleReplay.skip());
    document.getElementById("btn-sound").addEventListener("click", () => BattleReplay.toggleSound());
    document.querySelectorAll(".btn-speed").forEach((btn) => {
        btn.addEventListener("click", () => BattleReplay.setSpeed(parseFloat(btn.dataset.speed)));
    });
});
