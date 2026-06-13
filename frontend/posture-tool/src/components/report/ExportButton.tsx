export default function ExportButton() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="
        rounded-full
        bg-slate-900
        px-6
        py-3
        text-white
        transition
        hover:bg-slate-800
      "
    >
      Export Report
    </button>
  )
}