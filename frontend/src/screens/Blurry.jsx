export default function Blurry({ onRetake, onUpload }) {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center px-6 text-center">
      <div className="grid h-16 w-16 place-items-center rounded-full bg-rose-100 text-3xl text-rose-600">
        !
      </div>
      <h2 className="mt-5 text-lg font-bold">That photo is too blurry</h2>
      <p className="mt-2 text-sm text-slate-500">
        We need a sharper image to read the card reliably.
      </p>

      <div className="mt-8 w-full space-y-3">
        <button className="btn-primary w-full" onClick={onRetake}>
          Retake with camera
        </button>
        <label className="btn-ghost w-full cursor-pointer">
          Choose another photo
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
          />
        </label>
      </div>
    </div>
  )
}
