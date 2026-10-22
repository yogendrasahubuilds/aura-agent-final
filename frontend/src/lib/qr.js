const GF_EXP = new Array(512);
const GF_LOG = new Array(256);
let gfValue = 1;
for (let index = 0; index < 255; index += 1) {
  GF_EXP[index] = gfValue;
  GF_LOG[gfValue] = index;
  gfValue <<= 1;
  if (gfValue & 0x100) gfValue ^= 0x11d;
}
for (let index = 255; index < GF_EXP.length; index += 1) GF_EXP[index] = GF_EXP[index - 255];

function gfMultiply(left, right) {
  return left && right ? GF_EXP[GF_LOG[left] + GF_LOG[right]] : 0;
}

function errorCorrection(data) {
  let polynomial = [1];
  for (let root = 0; root < 7; root += 1) {
    const next = new Array(polynomial.length + 1).fill(0);
    polynomial.forEach((coefficient, index) => {
      next[index] ^= coefficient;
      next[index + 1] ^= gfMultiply(coefficient, GF_EXP[root]);
    });
    polynomial = next;
  }
  const remainder = new Array(7).fill(0);
  data.forEach((byte) => {
    const factor = byte ^ remainder.shift();
    remainder.push(0);
    for (let index = 0; index < 7; index += 1) remainder[index] ^= gfMultiply(polynomial[index + 1], factor);
  });
  return remainder;
}

function putFinder(matrix, reserved, left, top) {
  for (let y = -1; y <= 7; y += 1) {
    for (let x = -1; x <= 7; x += 1) {
      const row = top + y;
      const column = left + x;
      if (row < 0 || row >= 21 || column < 0 || column >= 21) continue;
      reserved[row][column] = true;
      matrix[row][column] = x >= 0 && x <= 6 && y >= 0 && y <= 6
        && (x === 0 || x === 6 || y === 0 || y === 6 || (x >= 2 && x <= 4 && y >= 2 && y <= 4));
    }
  }
}

function formatBits(mask) {
  const value = (1 << 3) | mask;
  let remainder = value << 10;
  while (remainder.toString(2).length >= 11) {
    remainder ^= 0x537 << (remainder.toString(2).length - 11);
  }
  return ((value << 10) | remainder) ^ 0x5412;
}

export function makeBookingQr(value) {
  const bytes = Array.from(new TextEncoder().encode(String(value)));
  if (bytes.length > 17) throw new RangeError("Booking ID exceeds the supported QR payload length.");
  const bits = [0, 1, 0, 0];
  for (let shift = 7; shift >= 0; shift -= 1) bits.push((bytes.length >> shift) & 1);
  bytes.forEach((byte) => {
    for (let shift = 7; shift >= 0; shift -= 1) bits.push((byte >> shift) & 1);
  });
  for (let count = Math.min(4, 152 - bits.length); count > 0; count -= 1) bits.push(0);
  while (bits.length % 8) bits.push(0);
  const data = [];
  for (let index = 0; index < bits.length; index += 8) {
    data.push(bits.slice(index, index + 8).reduce((byte, bit) => (byte << 1) | bit, 0));
  }
  for (let pad = 0; data.length < 19; pad += 1) data.push(pad % 2 ? 0x11 : 0xec);
  const codewords = [...data, ...errorCorrection(data)];
  const stream = codewords.flatMap((byte) => Array.from({ length: 8 }, (_, index) => (byte >> (7 - index)) & 1));

  const matrix = Array.from({ length: 21 }, () => new Array(21).fill(false));
  const reserved = Array.from({ length: 21 }, () => new Array(21).fill(false));
  putFinder(matrix, reserved, 0, 0);
  putFinder(matrix, reserved, 14, 0);
  putFinder(matrix, reserved, 0, 14);
  for (let index = 8; index < 13; index += 1) {
    matrix[6][index] = index % 2 === 0;
    matrix[index][6] = index % 2 === 0;
    reserved[6][index] = true;
    reserved[index][6] = true;
  }

  const reservedFormat = (row, column, bit) => {
    matrix[row][column] = Boolean((formatBits(0) >> bit) & 1);
    reserved[row][column] = true;
  };
  for (let bit = 0; bit <= 5; bit += 1) reservedFormat(bit, 8, bit);
  reservedFormat(7, 8, 6);
  reservedFormat(8, 8, 7);
  reservedFormat(8, 7, 8);
  for (let bit = 9; bit < 15; bit += 1) reservedFormat(8, 14 - bit, bit);
  for (let bit = 0; bit < 8; bit += 1) reservedFormat(8, 20 - bit, bit);
  for (let bit = 8; bit < 15; bit += 1) reservedFormat(20 - 14 + bit, 8, bit);
  matrix[13][8] = true;
  reserved[13][8] = true;

  let streamIndex = 0;
  for (let right = 20; right >= 1; right -= 2) {
    if (right === 6) right -= 1;
    for (let vertical = 0; vertical < 21; vertical += 1) {
      const row = ((right + 1) & 2) === 0 ? 20 - vertical : vertical;
      for (let offset = 0; offset < 2; offset += 1) {
        const column = right - offset;
        if (reserved[row][column]) continue;
        const bit = streamIndex < stream.length ? stream[streamIndex] : 0;
        matrix[row][column] = Boolean(bit ^ (((row + column) % 2) === 0));
        streamIndex += 1;
      }
    }
  }
  return matrix;
}
