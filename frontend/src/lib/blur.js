// Variance-of-Laplacian sharpness score on a downscaled grayscale copy.
// Higher = sharper. Mirrors the backend guard (thresholds are tuned separately
// because the image scale differs).

export function sharpnessScore(source) {
  const target = 320
  const ratio = source.width / source.height
  const w = ratio >= 1 ? target : Math.round(target * ratio)
  const h = ratio >= 1 ? Math.round(target / ratio) : target

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(source, 0, 0, w, h)
  const { data } = ctx.getImageData(0, 0, w, h)

  // grayscale (luma)
  const gray = new Float64Array(w * h)
  for (let i = 0; i < w * h; i++) {
    gray[i] = 0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2]
  }

  // 3x3 Laplacian, collect responses on the interior
  let sum = 0
  let sumSq = 0
  let count = 0
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const idx = y * w + x
      const v =
        -gray[idx - w] -
        gray[idx - 1] +
        4 * gray[idx] -
        gray[idx + 1] -
        gray[idx + w]
      sum += v
      sumSq += v * v
      count++
    }
  }
  if (count === 0) return 0
  const mean = sum / count
  return sumSq / count - mean * mean
}
