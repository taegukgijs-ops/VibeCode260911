const boardCanvas = document.getElementById("gameCanvas");
const nextCanvas = document.getElementById("nextCanvas");
const boardContext = boardCanvas.getContext("2d");
const nextContext = nextCanvas.getContext("2d");
const overlay = document.getElementById("overlay");
const startButton = document.getElementById("startButton");
const pauseButton = document.getElementById("pauseButton");
const restartButton = document.getElementById("restartButton");
const scoreElement = document.getElementById("score");
const linesElement = document.getElementById("lines");
const levelElement = document.getElementById("level");
const levelLabel = document.getElementById("levelLabel");
const statusText = document.getElementById("statusText");

const columns = 10;
const rows = 20;
const cellSize = boardCanvas.width / columns;
const colors = [null, "#57f3dc", "#5c7cff", "#ff9f43", "#ffd85a", "#9d72ff", "#63e66d", "#ff4e97"];
const pieces = [
  [[1, 1, 1, 1]],
  [[2, 0, 0], [2, 2, 2]],
  [[0, 0, 3], [3, 3, 3]],
  [[4, 4], [4, 4]],
  [[0, 5, 0], [5, 5, 5]],
  [[0, 6, 6], [6, 6, 0]],
  [[7, 7, 0], [0, 7, 7]]
];

let board = createBoard();
let activePiece = null;
let nextPiece = randomPiece();
let score = 0;
let lines = 0;
let level = 1;
let dropCounter = 0;
let lastTime = 0;
let animationId = null;
let gameState = "ready";

function createBoard() {
  return Array.from({ length: rows }, () => Array(columns).fill(0));
}

function randomPiece() {
  const shape = pieces[Math.floor(Math.random() * pieces.length)].map((row) => [...row]);
  return { shape, x: Math.floor((columns - shape[0].length) / 2), y: 0 };
}

function drawCell(context, x, y, colorIndex, size) {
  const color = colors[colorIndex];
  context.fillStyle = color;
  context.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);
  context.fillStyle = "rgba(255,255,255,.24)";
  context.fillRect(x * size + 2, y * size + 2, size - 4, 3);
  context.fillStyle = "rgba(0,0,0,.18)";
  context.fillRect(x * size + 2, y * size + size - 5, size - 4, 3);
}

function drawBoard() {
  boardContext.fillStyle = "#090b15";
  boardContext.fillRect(0, 0, boardCanvas.width, boardCanvas.height);
  boardContext.strokeStyle = "rgba(116, 132, 188, .08)";
  boardContext.lineWidth = 1;
  for (let x = 0; x <= columns; x += 1) {
    boardContext.beginPath();
    boardContext.moveTo(x * cellSize + .5, 0);
    boardContext.lineTo(x * cellSize + .5, boardCanvas.height);
    boardContext.stroke();
  }
  for (let y = 0; y <= rows; y += 1) {
    boardContext.beginPath();
    boardContext.moveTo(0, y * cellSize + .5);
    boardContext.lineTo(boardCanvas.width, y * cellSize + .5);
    boardContext.stroke();
  }
  board.forEach((row, y) => row.forEach((value, x) => value && drawCell(boardContext, x, y, value, cellSize)));
  if (activePiece) {
    drawGhost();
    activePiece.shape.forEach((row, y) => row.forEach((value, x) => value && drawCell(boardContext, activePiece.x + x, activePiece.y + y, value, cellSize)));
  }
}

function drawGhost() {
  const ghost = { ...activePiece, y: activePiece.y };
  while (!collides(ghost, 0, 1)) ghost.y += 1;
  boardContext.globalAlpha = .2;
  ghost.shape.forEach((row, y) => row.forEach((value, x) => value && drawCell(boardContext, ghost.x + x, ghost.y + y, value, cellSize)));
  boardContext.globalAlpha = 1;
}

function drawNext() {
  const size = 32;
  nextContext.fillStyle = "#0b0e1b";
  nextContext.fillRect(0, 0, nextCanvas.width, nextCanvas.height);
  const offsetX = (4 - nextPiece.shape[0].length) / 2;
  const offsetY = (4 - nextPiece.shape.length) / 2;
  nextPiece.shape.forEach((row, y) => row.forEach((value, x) => value && drawCell(nextContext, offsetX + x, offsetY + y, value, size)));
}

function collides(piece, moveX = 0, moveY = 0, shape = piece.shape) {
  return shape.some((row, y) => row.some((value, x) => {
    if (!value) return false;
    const boardX = piece.x + x + moveX;
    const boardY = piece.y + y + moveY;
    return boardX < 0 || boardX >= columns || boardY >= rows || (boardY >= 0 && board[boardY][boardX]);
  }));
}

function mergePiece() {
  activePiece.shape.forEach((row, y) => row.forEach((value, x) => {
    if (value && activePiece.y + y >= 0) board[activePiece.y + y][activePiece.x + x] = value;
  }));
}

function clearLines() {
  let cleared = 0;
  board = board.filter((row) => {
    if (row.every(Boolean)) { cleared += 1; return false; }
    return true;
  });
  while (board.length < rows) board.unshift(Array(columns).fill(0));
  if (cleared) {
    const points = [0, 100, 300, 500, 800][cleared] * level;
    score += points;
    lines += cleared;
    level = Math.floor(lines / 10) + 1;
    updateStats();
  }
}

function rotate(shape) {
  return shape[0].map((_, index) => shape.map((row) => row[index]).reverse());
}

function rotatePiece() {
  if (gameState !== "playing") return;
  const rotated = rotate(activePiece.shape);
  const offsets = [0, -1, 1, -2, 2];
  for (const offset of offsets) {
    if (!collides(activePiece, offset, 0, rotated)) {
      activePiece.x += offset;
      activePiece.shape = rotated;
      drawBoard();
      return;
    }
  }
}

function movePiece(direction) {
  if (gameState === "playing" && !collides(activePiece, direction, 0)) {
    activePiece.x += direction;
    drawBoard();
  }
}

function dropPiece() {
  if (gameState !== "playing") return;
  if (!collides(activePiece, 0, 1)) {
    activePiece.y += 1;
    dropCounter = 0;
  } else {
    lockPiece();
  }
  drawBoard();
}

function hardDrop() {
  if (gameState !== "playing") return;
  let distance = 0;
  while (!collides(activePiece, 0, 1)) { activePiece.y += 1; distance += 1; }
  score += distance * 2;
  updateStats();
  lockPiece();
  drawBoard();
}

function lockPiece() {
  mergePiece();
  clearLines();
  activePiece = nextPiece;
  nextPiece = randomPiece();
  drawNext();
  if (collides(activePiece)) endGame();
}

function updateStats() {
  scoreElement.textContent = String(score).padStart(6, "0");
  linesElement.textContent = String(lines).padStart(3, "0");
  levelElement.textContent = String(level).padStart(2, "0");
  levelLabel.textContent = `LV ${String(level).padStart(2, "0")}`;
}

function resetGame() {
  board = createBoard();
  score = 0;
  lines = 0;
  level = 1;
  nextPiece = randomPiece();
  activePiece = randomPiece();
  gameState = "playing";
  dropCounter = 0;
  overlay.classList.add("hidden");
  pauseButton.disabled = false;
  pauseButton.textContent = "일시정지";
  statusText.textContent = "RUNNING";
  updateStats();
  drawNext();
  drawBoard();
  if (animationId === null) animationId = requestAnimationFrame(update);
}

function endGame() {
  gameState = "over";
  pauseButton.disabled = true;
  statusText.textContent = "GAME OVER";
  overlay.innerHTML = '<p class="overlay-kicker">RUN COMPLETE</p><h1>게임 종료</h1><p>최종 점수: ' + String(score).padStart(6, "0") + '</p><button id="startButton" class="primary-button">다시 시작</button>';
  overlay.classList.remove("hidden");
  document.getElementById("startButton").addEventListener("click", resetGame);
}

function togglePause() {
  if (gameState === "playing") {
    gameState = "paused";
    pauseButton.textContent = "계속하기";
    statusText.textContent = "PAUSED";
    overlay.innerHTML = '<p class="overlay-kicker">SYSTEM PAUSED</p><h1>일시정지</h1><p>계속해서 블록을 쌓아보세요.</p><button id="resumeButton" class="primary-button">계속하기</button>';
    overlay.classList.remove("hidden");
    document.getElementById("resumeButton").addEventListener("click", togglePause);
  } else if (gameState === "paused") {
    gameState = "playing";
    pauseButton.textContent = "일시정지";
    statusText.textContent = "RUNNING";
    overlay.classList.add("hidden");
  }
}

function update(time = 0) {
  const delta = time - lastTime;
  lastTime = time;
  if (gameState === "playing") {
    dropCounter += delta;
    const dropInterval = Math.max(90, 800 - (level - 1) * 65);
    if (dropCounter > dropInterval) dropPiece();
    drawBoard();
  }
  animationId = requestAnimationFrame(update);
}

function handleKey(event) {
  const keys = ["ArrowLeft", "ArrowRight", "ArrowDown", "ArrowUp", " ", "p", "P"];
  if (keys.includes(event.key)) event.preventDefault();
  if (event.key === "ArrowLeft") movePiece(-1);
  if (event.key === "ArrowRight") movePiece(1);
  if (event.key === "ArrowDown") dropPiece();
  if (event.key === "ArrowUp") rotatePiece();
  if (event.key === " ") hardDrop();
  if (event.key === "p" || event.key === "P") togglePause();
}

startButton.addEventListener("click", resetGame);
restartButton.addEventListener("click", resetGame);
pauseButton.addEventListener("click", togglePause);
document.addEventListener("keydown", handleKey);
drawNext();
drawBoard();
