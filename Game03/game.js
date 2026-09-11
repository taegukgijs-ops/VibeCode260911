const canvas = document.getElementById("gameCanvas");
const context = canvas.getContext("2d");
const startOverlay = document.getElementById("startOverlay");
const levelOverlay = document.getElementById("levelOverlay");
const levelMessage = document.getElementById("levelMessage");
const levelDetail = document.getElementById("levelDetail");
const startButton = document.getElementById("startButton");
const pauseButton = document.getElementById("pauseButton");
const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");
const timeLabel = document.getElementById("timeLabel");
const hpText = document.getElementById("hpText");
const hpBar = document.getElementById("hpBar");
const levelText = document.getElementById("levelText");
const xpText = document.getElementById("xpText");
const xpBar = document.getElementById("xpBar");
const killText = document.getElementById("killText");

const WORLD = { width: 2400, height: 1800 };
const colors = { ground: "#172426", grid: "rgba(167, 210, 183, .09)", player: "#9ee6aa", playerCore: "#f5f5e9", enemy: "#ee745c", enemyDark: "#6d3030", xp: "#ffd166", bullet: "#fff0a8" };
const keys = new Set();
let player;
let enemies = [];
let projectiles = [];
let gems = [];
let particles = [];
let state = "ready";
let elapsed = 0;
let spawnTimer = 0;
let lastTime = 0;
let animationId = null;

function resetGame() {
  player = { x: WORLD.width / 2, y: WORLD.height / 2, radius: 16, speed: 230, hp: 100, maxHp: 100, level: 1, xp: 0, nextXp: 30, kills: 0, attackTimer: 0, attackInterval: 650 };
  enemies = [];
  projectiles = [];
  gems = [];
  particles = [];
  elapsed = 0;
  spawnTimer = 450;
  state = "playing";
  startOverlay.classList.add("hidden");
  levelOverlay.classList.add("hidden");
  pauseButton.disabled = false;
  pauseButton.textContent = "일시정지";
  statusText.textContent = "SURVIVING";
  statusDot.className = "status-dot active";
  updateHud();
  if (animationId === null) animationId = requestAnimationFrame(loop);
}

function updateHud() {
  if (!player) return;
  const hpRatio = Math.max(0, player.hp / player.maxHp);
  const xpRatio = Math.min(1, player.xp / player.nextXp);
  hpText.textContent = `${Math.ceil(Math.max(0, player.hp))} / ${player.maxHp}`;
  hpBar.style.width = `${hpRatio * 100}%`;
  levelText.textContent = String(player.level).padStart(2, "0");
  xpText.textContent = `${player.xp} / ${player.nextXp}`;
  xpBar.style.width = `${xpRatio * 100}%`;
  killText.textContent = String(player.kills).padStart(3, "0");
  timeLabel.textContent = formatTime(elapsed);
}

function formatTime(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function distance(first, second) {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

function spawnEnemy() {
  const angle = Math.random() * Math.PI * 2;
  const radius = 470 + Math.random() * 180;
  const x = Math.max(30, Math.min(WORLD.width - 30, player.x + Math.cos(angle) * radius));
  const y = Math.max(30, Math.min(WORLD.height - 30, player.y + Math.sin(angle) * radius));
  const elite = Math.random() < Math.min(.08 + player.level * .012, .22);
  enemies.push({ x, y, radius: elite ? 23 : 16, speed: elite ? 47 : 62 + player.level * 2, hp: elite ? 3 : 1, maxHp: elite ? 3 : 1, elite, wobble: Math.random() * Math.PI * 2 });
}

function nearestEnemy() {
  return enemies.reduce((nearest, enemy) => !nearest || distance(player, enemy) < distance(player, nearest) ? enemy : nearest, null);
}

function autoAttack() {
  const target = nearestEnemy();
  if (!target || player.attackTimer > 0) return;
  const angle = Math.atan2(target.y - player.y, target.x - player.x);
  projectiles.push({ x: player.x, y: player.y, dx: Math.cos(angle) * 530, dy: Math.sin(angle) * 530, radius: 5, damage: 1, life: 1200 });
  player.attackTimer = player.attackInterval;
}

function addExperience(amount) {
  player.xp += amount;
  while (player.xp >= player.nextXp) {
    player.xp -= player.nextXp;
    player.level += 1;
    player.nextXp = Math.floor(player.nextXp * 1.35);
    player.attackInterval = Math.max(250, player.attackInterval - 38);
    player.speed += 7;
    player.maxHp += 5;
    player.hp = Math.min(player.maxHp, player.hp + 20);
    showLevelUp();
  }
}

function showLevelUp() {
  levelMessage.textContent = `LEVEL ${String(player.level).padStart(2, "0")}`;
  levelDetail.textContent = "공격 속도와 이동 속도가 상승했습니다.";
  levelOverlay.classList.remove("hidden");
  window.clearTimeout(showLevelUp.timeout);
  showLevelUp.timeout = window.setTimeout(() => levelOverlay.classList.add("hidden"), 1500);
}

function burst(x, y, color, amount = 8) {
  for (let index = 0; index < amount; index += 1) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 95;
    particles.push({ x, y, dx: Math.cos(angle) * speed, dy: Math.sin(angle) * speed, life: 350 + Math.random() * 250, maxLife: 600, color });
  }
}

function update(delta) {
  const seconds = delta / 1000;
  elapsed += delta;
  const horizontal = (keys.has("d") || keys.has("ArrowRight") ? 1 : 0) - (keys.has("a") || keys.has("ArrowLeft") ? 1 : 0);
  const vertical = (keys.has("s") || keys.has("ArrowDown") ? 1 : 0) - (keys.has("w") || keys.has("ArrowUp") ? 1 : 0);
  const length = Math.hypot(horizontal, vertical) || 1;
  player.x = Math.max(24, Math.min(WORLD.width - 24, player.x + horizontal / length * player.speed * seconds));
  player.y = Math.max(24, Math.min(WORLD.height - 24, player.y + vertical / length * player.speed * seconds));
  player.attackTimer -= delta;
  autoAttack();
  spawnTimer -= delta;
  if (spawnTimer <= 0) { spawnEnemy(); spawnTimer = Math.max(180, 720 - player.level * 25); }

  enemies.forEach((enemy) => {
    const angle = Math.atan2(player.y - enemy.y, player.x - enemy.x);
    enemy.x += Math.cos(angle) * enemy.speed * seconds;
    enemy.y += Math.sin(angle) * enemy.speed * seconds;
    enemy.wobble += seconds * 4;
    if (distance(player, enemy) < player.radius + enemy.radius) player.hp -= (enemy.elite ? 16 : 9) * seconds;
  });
  projectiles.forEach((shot) => { shot.x += shot.dx * seconds; shot.y += shot.dy * seconds; shot.life -= delta; });
  gems.forEach((gem) => {
    if (distance(player, gem) < 145) { const angle = Math.atan2(player.y - gem.y, player.x - gem.x); gem.x += Math.cos(angle) * 320 * seconds; gem.y += Math.sin(angle) * 320 * seconds; }
  });
  particles.forEach((particle) => { particle.x += particle.dx * seconds; particle.y += particle.dy * seconds; particle.life -= delta; });
  resolveCollisions();
  enemies = enemies.filter((enemy) => !enemy.destroyed);
  projectiles = projectiles.filter((shot) => shot.life > 0 && shot.x > 0 && shot.x < WORLD.width && shot.y > 0 && shot.y < WORLD.height);
  gems = gems.filter((gem) => !gem.collected);
  particles = particles.filter((particle) => particle.life > 0);
  if (player.hp <= 0) endGame();
  updateHud();
}

function resolveCollisions() {
  projectiles.forEach((shot) => enemies.forEach((enemy) => {
    if (!enemy.destroyed && distance(shot, enemy) < shot.radius + enemy.radius) {
      shot.life = 0;
      enemy.hp -= shot.damage;
      burst(shot.x, shot.y, colors.bullet, 3);
      if (enemy.hp <= 0) { enemy.destroyed = true; player.kills += 1; gems.push({ x: enemy.x, y: enemy.y, radius: 7, value: enemy.elite ? 12 : 6 }); burst(enemy.x, enemy.y, colors.enemy, enemy.elite ? 16 : 8); }
    }
  }));
  gems.forEach((gem) => {
    if (!gem.collected && distance(player, gem) < player.radius + gem.radius + 5) { gem.collected = true; addExperience(gem.value); burst(gem.x, gem.y, colors.xp, 4); }
  });
}

function drawWorld() {
  const cameraX = Math.max(0, Math.min(WORLD.width - canvas.width, player.x - canvas.width / 2));
  const cameraY = Math.max(0, Math.min(WORLD.height - canvas.height, player.y - canvas.height / 2));
  context.fillStyle = colors.ground; context.fillRect(0, 0, canvas.width, canvas.height);
  context.save(); context.translate(-cameraX, -cameraY);
  context.strokeStyle = colors.grid; context.lineWidth = 1;
  for (let x = 0; x <= WORLD.width; x += 48) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, WORLD.height); context.stroke(); }
  for (let y = 0; y <= WORLD.height; y += 48) { context.beginPath(); context.moveTo(0, y); context.lineTo(WORLD.width, y); context.stroke(); }
  gems.forEach((gem) => { context.save(); context.translate(gem.x, gem.y); context.rotate(Math.PI / 4); context.fillStyle = colors.xp; context.shadowColor = colors.xp; context.shadowBlur = 12; context.fillRect(-7, -7, 14, 14); context.restore(); });
  projectiles.forEach((shot) => { context.fillStyle = colors.bullet; context.shadowColor = colors.bullet; context.shadowBlur = 12; context.beginPath(); context.arc(shot.x, shot.y, shot.radius, 0, Math.PI * 2); context.fill(); context.shadowBlur = 0; });
  enemies.forEach((enemy) => { context.save(); context.translate(enemy.x, enemy.y); context.fillStyle = enemy.elite ? "#ffaf68" : colors.enemy; context.shadowColor = context.fillStyle; context.shadowBlur = 10; context.beginPath(); context.arc(0, 0, enemy.radius, 0, Math.PI * 2); context.fill(); context.shadowBlur = 0; context.fillStyle = colors.enemyDark; context.beginPath(); context.arc(Math.sin(enemy.wobble) * 3, Math.cos(enemy.wobble) * 3, enemy.radius * .42, 0, Math.PI * 2); context.fill(); context.restore(); });
  particles.forEach((particle) => { context.globalAlpha = Math.max(0, particle.life / particle.maxLife); context.fillStyle = particle.color; context.fillRect(particle.x - 2, particle.y - 2, 4, 4); context.globalAlpha = 1; });
  drawPlayer();
  context.restore();
}

function drawPlayer() {
  const aim = nearestEnemy();
  const angle = aim ? Math.atan2(aim.y - player.y, aim.x - player.x) : 0;
  context.save(); context.translate(player.x, player.y); context.rotate(angle);
  context.fillStyle = colors.player; context.shadowColor = colors.player; context.shadowBlur = 18;
  context.beginPath(); context.moveTo(23, 0); context.lineTo(-12, -14); context.lineTo(-8, 0); context.lineTo(-12, 14); context.closePath(); context.fill(); context.shadowBlur = 0;
  context.fillStyle = colors.playerCore; context.beginPath(); context.arc(2, 0, 6, 0, Math.PI * 2); context.fill(); context.restore();
}

function draw() { drawWorld(); }

function togglePause() {
  if (state === "playing") { state = "paused"; statusText.textContent = "PAUSED"; statusDot.className = "status-dot"; pauseButton.textContent = "계속하기"; }
  else if (state === "paused") { state = "playing"; statusText.textContent = "SURVIVING"; statusDot.className = "status-dot active"; pauseButton.textContent = "일시정지"; }
}

function endGame() { state = "over"; pauseButton.disabled = true; statusText.textContent = "RUN ENDED"; statusDot.className = "status-dot alert"; startOverlay.innerHTML = `<p class="kicker">SURVIVAL REPORT</p><h1>RUN ENDED</h1><p>레벨 ${player.level} · 처치 ${player.kills} · 생존 시간 ${formatTime(elapsed)}</p><button id="restartButton" class="primary-button">RESTART <span>→</span></button>`; startOverlay.classList.remove("hidden"); document.getElementById("restartButton").addEventListener("click", resetGame); }

function loop(time = 0) { const delta = Math.min(40, time - lastTime || 16); lastTime = time; if (state === "playing") update(delta); draw(); animationId = requestAnimationFrame(loop); }

function handleKey(event) {
  const key = event.key;
  if (["w", "a", "s", "d", "W", "A", "S", "D", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "p", "P"].includes(key)) event.preventDefault();
  if (key === "p" || key === "P") { togglePause(); return; }
  keys.add(key.toLowerCase());
}

document.addEventListener("keydown", handleKey);
document.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));
startButton.addEventListener("click", resetGame);
pauseButton.addEventListener("click", togglePause);
player = { x: WORLD.width / 2, y: WORLD.height / 2, radius: 16, hp: 100, maxHp: 100, level: 1, xp: 0, nextXp: 30, kills: 0, attackTimer: 0, attackInterval: 650, speed: 230 };
draw();