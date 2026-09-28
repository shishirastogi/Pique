const assetPathPrefix = "/assets";

/** Forest backdrop used by the Welcome / HowItWorks / Locked screens. */
export default function SceneBackground({ className = "" }: { className?: string }) {
  return (
    <img
      src={`${assetPathPrefix}/background.png`}
      alt=""
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 h-full w-full select-none object-cover ${className}`}
    />
  );
}
