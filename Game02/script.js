const canvas = document.getElementById("gameCanvas");
const context = canvas.getContext("2d");
const overlay = document.getElementById("overlay");
const startButton = document.getElementById("startButton");
const pauseButton = document.getElementById("pauseButton");
const restartButton = document.getElementById("restartButton");
const scoreElement = document.getElementById("score");
const highScoreElement = document.getElementById("highScore");
const waveElement = document.getElementById("wave");
const livesElement = document.getElementById("lives");
const powerElement = document.getElementById("power");
const waveLabel = document.getElementById("waveLabel");
const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");

const width = canvas.width;
const height = canvas.height;
const keys = new Set();
const colors = { lime: "#d7f36b", orange: "#ff9e45", aqua: "#62e6d2", red: "#f05d5e", white: "#f5f6ec" };
let player = { x: width / 2, y: height - 84, invincible: 0 };
let bullets = [];
let bombs = [];
let enemies = [];
let targets = [];
let items = [];
let particles = [];
let score = 0;
let highScore = Number(localStorage.getItem("skyRaidHighScore") || 0);
let wave = 1;
let lives = 3;
let gameState = "ready";
let lastTime = 0;
let spawnTimer = 0;
let targetTimer = 0;
let itemTimer = 0;
let animationId = null;

function resetGame() {
  player = { x: width / 2, y: height - 84, speed: 280, cooldown: 0, bombCooldown: 0, invincible: 0, powerLevel: 0, powerTimer: 0 };
  bullets = [];
  bombs = [];
  enemies = [];
  targets = [];
  items = [];
  particles = [];
  score = 0;
  wave = 1;
  lives = 3;
  spawnTimer = 0;
  targetTimer = 500;
  itemTimer = 1800;
  gameState = "playing";
  overlay.classList.add("hidden");
  pauseButton.disabled = false;
  pauseButton.textContent = "일시정지";
  statusText.textContent = "COMBAT ACTIVE";
  statusDot.classList.remove("alert");
  updateHud();
  if (animationId === null) animationId = requestAnimationFrame(loop);
}

function updateHud() {
  scoreElement.textContent = String(score).padStart(6, "0");
  highScoreElement.textContent = String(Math.max(highScore, score)).padStart(6, "0");
  waveElement.textContent = String(wave).padStart(2, "0");
  waveLabel.textContent = `WAVE ${String(wave).padStart(2, "0")}`;
  livesElement.textContent = `${"● ".repeat(lives)}${"○ ".repeat(3 - lives)}`.trim();
  const powerSeconds = Math.ceil(Math.max(0, player.powerTimer) / 1000);
  powerElement.textContent = player.powerLevel ? `LV ${player.powerLevel} / ${powerSeconds}s` : "READY";
  powerElement.classList.toggle("powered", Boolean(player.powerLevel));
}

function addScore(points) {
  score += points;
  if (score > highScore) { highScore = score; localStorage.setItem("skyRaidHighScore", highScore); }
  updateHud();
}

function fire() {
  if (player.cooldown > 0) return;
  const offsets = player.powerLevel ? [-18, 0, 18] : [-11, 11];
  offsets.forEach((offset) => bullets.push({ x: player.x + offset, y: player.y - 22, speed: 490, ground: false }));
  player.cooldown = 125;
}

function dropBomb() {
  if (player.bombCooldown > 0) return;
  bombs.push({ x: player.x, y: player.y - 6, radius: 3, speed: 180, life: 950 });
  player.bombCooldown = 850;
}

function spawnEnemy() {
  const type = Math.random() > .72 ? "heavy" : "scout";
  enemies.push({ x: 28 + Math.random() * (width - 56), y: -30, type, speed: type === "heavy" ? 54 : 84 + wave * 4, phase: Math.random() * Math.PI * 2, hp: type === "heavy" ? 2 : 1 });
}

function spawnTarget() {
  targets.push({ x: 25 + Math.random() * (width - 50), y: -24, speed: 50 + wave * 3, hp: 1, rotation: Math.random() * Math.PI });
}

function spawnItem() {
  items.push({ x: 28 + Math.random() * (width - 56), y: -24, speed: 68, rotation: 0, pulse: Math.random() * Math.PI * 2 });
}

function burst(x, y, color, amount = 10) {
  for (let index = 0; index < amount; index += 1) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 120;
    particles.push({ x, y, dx: Math.cos(angle) * speed, dy: Math.sin(angle) * speed, life: 380 + Math.random() * 350, maxLife: 700, color });
  }
}

function hitPlayer() {
  if (player.invincible > 0) return;
  lives -= 1;
  player.invincible = 1500;
  burst(player.x, player.y, colors.orange, 20);
  updateHud();
  if (lives <= 0) endGame();
}

function update(delta) {
  const seconds = delta / 1000;
  const horizontal = (keys.has("ArrowRight") ? 1 : 0) - (keys.has("ArrowLeft") ? 1 : 0);
  const vertical = (keys.has("ArrowDown") ? 1 : 0) - (keys.has("ArrowUp") ? 1 : 0);
  player.x = Math.max(20, Math.min(width - 20, player.x + horizontal * player.speed * seconds));
  player.y = Math.max(height * .48, Math.min(height - 32, player.y + vertical * player.speed * seconds));
  if (keys.has("z") || keys.has("Z")) fire();
  if (keys.has("x") || keys.has("X")) dropBomb();
  player.cooldown -= delta; player.bombCooldown -= delta; player.invincible -= delta;

  spawnTimer -= delta;
  if (spawnTimer <= 0) { spawnEnemy(); spawnTimer = Math.max(260, 830 - wave * 40); }
  targetTimer -= delta;
  if (targetTimer <= 0) { spawnTarget(); targetTimer = 1350; }
  itemTimer -= delta;
  if (itemTimer <= 0) { spawnItem(); itemTimer = 8500 + Math.random() * 3500; }
  bullets.forEach((bullet) => { bullet.y -= bullet.speed * seconds; });
  bombs.forEach((bomb) => { bomb.y += bomb.speed * seconds; bomb.radius += 18 * seconds; bomb.life -= delta; });
  enemies.forEach((enemy) => { enemy.y += enemy.speed * seconds; enemy.x += Math.sin(enemy.y / 45 + enemy.phase) * 35 * seconds; });
  targets.forEach((target) => { target.y += target.speed * seconds; target.rotation += seconds; });
  items.forEach((item) => { item.y += item.speed * seconds; item.rotation += seconds * 2; item.pulse += seconds * 5; });
  particles.forEach((particle) => { particle.x += particle.dx * seconds; particle.y += particle.dy * seconds; particle.life -= delta; });
  player.powerTimer -= delta;
  if (player.powerTimer <= 0) player.powerLevel = 0;
  updateHud();
  resolveCollisions();
  bullets = bullets.filter((bullet) => bullet.y > -20);
  bombs = bombs.filter((bomb) => bomb.y < height + 40 && bomb.life > 0);
  enemies = enemies.filter((enemy) => enemy.y < height + 40 && !enemy.destroyed);
  targets = targets.filter((target) => target.y < height + 40 && !target.destroyed);
  items = items.filter((item) => item.y < height + 40 && !item.collected);
  particles = particles.filter((particle) => particle.life > 0);
  if (score > 0 && score % 1200 < 30) { wave = Math.floor(score / 1200) + 1; updateHud(); }
}

function resolveCollisions() {
  bullets.forEach((bullet) => {
    enemies.forEach((enemy) => {
      if (!enemy.destroyed && Math.hypot(bullet.x - enemy.x, bullet.y - enemy.y) < (enemy.type === "heavy" ? 25 : 18)) {
        bullet.y = -100; enemy.hp -= 1; burst(bullet.x, bullet.y, colors.orange, 3);
        if (enemy.hp <= 0) { enemy.destroyed = true; addScore(enemy.type === "heavy" ? 250 : 100); burst(enemy.x, enemy.y, colors.orange, 14); }
      }
    });
  });
  bombs.forEach((bomb) => {
    targets.forEach((target) => {
      if (!target.destroyed && Math.hypot(bomb.x - target.x, bomb.y - target.y) < bomb.radius + 22) { target.destroyed = true; bomb.life = 0; addScore(180); burst(target.x, target.y, colors.lime, 16); }
    });
  });
  enemies.forEach((enemy) => {
    if (!enemy.destroyed && Math.hypot(player.x - enemy.x, player.y - enemy.y) < 25) { enemy.destroyed = true; hitPlayer(); }
  });
  targets.forEach((target) => {
    if (!target.destroyed && Math.hypot(player.x - target.x, player.y - target.y) < 25) { target.destroyed = true; hitPlayer(); }
  });
  items.forEach((item) => {
    if (!item.collected && Math.hypot(player.x - item.x, player.y - item.y) < 29) {
      item.collected = true;
      player.powerLevel = Math.min(3, player.powerLevel + 1);
      player.powerTimer = 10000;
      addScore(50);
      burst(item.x, item.y, colors.lime, 20);
    }
  });
}

function drawBackground() {
  context.fillStyle = "#071013"; context.fillRect(0, 0, width, height);
  context.strokeStyle = "rgba(98, 230, 210, .09)"; context.lineWidth = 1;
  const offset = (performance.now() / 18) % 48;
  for (let y = -48 + offset; y < height; y += 48) { context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke(); }
  for (let x = 0; x < width; x += 48) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, height); context.stroke(); }
  context.fillStyle = "rgba(98, 230, 210, .22)";
  for (let index = 0; index < 34; index += 1) { const x = (index * 113) % width; const y = (index * 77 + performance.now() / 9) % height; context.fillRect(x, y, 1, 4); }
}

function drawPlayer() {
  if (player.invincible > 0 && Math.floor(player.invincible / 100) % 2 === 0) return;
  context.save(); context.translate(player.x, player.y);
  context.fillStyle = colors.aqua; context.shadowColor = colors.aqua; context.shadowBlur = 12;
  context.beginPath(); context.moveTo(0, -27); context.lineTo(8, -7); context.lineTo(27, 13); context.lineTo(8, 10); context.lineTo(0, 27); context.lineTo(-8, 10); context.lineTo(-27, 13); context.lineTo(-8, -7); context.closePath(); context.fill();
  context.shadowBlur = 0; context.fillStyle = colors.white; context.fillRect(-3, -12, 6, 20); context.fillStyle = colors.orange; context.fillRect(-4, 19, 8, 9); context.restore();
}

function drawEntities() {
  bullets.forEach((bullet) => { context.fillStyle = colors.lime; context.shadowColor = colors.lime; context.shadowBlur = 9; context.fillRect(bullet.x - 2, bullet.y - 9, 4, 14); context.shadowBlur = 0; });
  bombs.forEach((bomb) => { context.strokeStyle = colors.orange; context.lineWidth = 2; context.beginPath(); context.arc(bomb.x, bomb.y, bomb.radius, 0, Math.PI * 2); context.stroke(); });
  enemies.forEach((enemy) => { context.save(); context.translate(enemy.x, enemy.y); context.fillStyle = enemy.type === "heavy" ? colors.red : colors.orange; context.beginPath(); context.moveTo(0, 20); context.lineTo(25, -10); context.lineTo(7, -8); context.lineTo(0, -24); context.lineTo(-7, -8); context.lineTo(-25, -10); context.closePath(); context.fill(); context.fillStyle = "#3b1d1d"; context.fillRect(-5, -7, 10, 13); context.restore(); });
  targets.forEach((target) => { context.save(); context.translate(target.x, target.y); context.rotate(target.rotation); context.fillStyle = colors.lime; context.fillRect(-15, -15, 30, 30); context.fillStyle = "#34431e"; context.fillRect(-7, -7, 14, 14); context.restore(); });
  items.forEach((item) => {
    context.save(); context.translate(item.x, item.y); context.rotate(item.rotation);
    const size = 14 + Math.sin(item.pulse) * 2;
    context.shadowColor = colors.lime; context.shadowBlur = 14; context.fillStyle = colors.lime;
    context.fillRect(-size, -size, size * 2, size * 2); context.shadowBlur = 0;
    context.fillStyle = "#263719"; context.font = "700 17px Space Mono"; context.textAlign = "center"; context.textBaseline = "middle"; context.fillText("P", 0, 1); context.restore();
  });
  particles.forEach((particle) => { context.globalAlpha = Math.max(0, particle.life / particle.maxLife); context.fillStyle = particle.color; context.fillRect(particle.x, particle.y, 3, 3); context.globalAlpha = 1; });
}

function draw() { drawBackground(); drawEntities(); drawPlayer(); }

function togglePause() {
  if (gameState === "playing") { gameState = "paused"; pauseButton.textContent = "계속하기"; statusText.textContent = "PAUSED"; statusDot.classList.add("alert"); showOverlay("SYSTEM PAUSED", "일시정지", "전장을 잠시 멈췄습니다.", "계속하기", togglePause); }
  else if (gameState === "paused") { gameState = "playing"; pauseButton.textContent = "일시정지"; statusText.textContent = "COMBAT ACTIVE"; statusDot.classList.remove("alert"); overlay.classList.add("hidden"); }
}

function showOverlay(kicker, title, message, buttonText, action) {
  overlay.innerHTML = `<p class="overlay-kicker">${kicker}</p><h1>${title}</h1><p>${message}</p><button class="primary-button">${buttonText} <span>→</span></button>`;
  overlay.classList.remove("hidden"); overlay.querySelector("button").addEventListener("click", action);
}

function endGame() { gameState = "over"; pauseButton.disabled = true; statusText.textContent = "MISSION FAILED"; statusDot.classList.add("alert"); showOverlay("MISSION REPORT", "전투 종료", `획득 점수: ${String(score).padStart(6, "0")}`, "다시 출격", resetGame); }

function loop(time = 0) {
  const delta = Math.min(40, time - lastTime || 16); lastTime = time;
  if (gameState === "playing") update(delta);
  draw(); animationId = requestAnimationFrame(loop);
}

function handleKey(event) {
  if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", " ", "z", "Z", "x", "X", "p", "P"].includes(event.key)) event.preventDefault();
  if (event.key === "p" || event.key === "P") { togglePause(); return; }
  keys.add(event.key);
}

document.addEventListener("keydown", handleKey);
document.addEventListener("keyup", (event) => keys.delete(event.key));
startButton.addEventListener("click", resetGame);
restartButton.addEventListener("click", resetGame);
pauseButton.addEventListener("click", togglePause);
highScoreElement.textContent = String(highScore).padStart(6, "0");
player = { x: width / 2, y: height - 84, invincible: 0, powerLevel: 0, powerTimer: 0 };
updateHud();
draw();