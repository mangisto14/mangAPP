/** Reusable skeleton shimmer blocks for loading states */

function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonStatCards() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card flex flex-col items-center gap-2 py-4">
            <SkeletonBlock className="h-9 w-16 rounded-lg" />
            <SkeletonBlock className="h-3 w-20 rounded" />
          </div>
        ))}
      </div>
      <div className="card space-y-3">
        <SkeletonBlock className="h-5 w-24 rounded" />
        {[...Array(4)].map((_, i) => (
          <div key={i} className="p-3 rounded-xl border border-bg-border space-y-2">
            <div className="flex justify-between items-center">
              <SkeletonBlock className="h-4 w-28 rounded" />
              <SkeletonBlock className="h-5 w-20 rounded-full" />
            </div>
            <SkeletonBlock className="h-2 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonShiftCards() {
  return (
    <div className="space-y-4">
      {[...Array(3)].map((_, g) => (
        <div key={g} className="space-y-2">
          <SkeletonBlock className="h-6 w-32 rounded-full" />
          {[...Array(2)].map((_, i) => (
            <div key={i} className="card space-y-2">
              <div className="flex justify-between">
                <SkeletonBlock className="h-4 w-24 rounded" />
                <SkeletonBlock className="h-4 w-16 rounded" />
              </div>
              <SkeletonBlock className="h-3 w-40 rounded" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonGuardCards() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="rounded-xl border border-bg-border p-3 flex justify-between items-center">
          <SkeletonBlock className="h-4 w-28 rounded" />
          <SkeletonBlock className="h-7 w-7 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonAbsenceCards() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="card flex justify-between items-center">
          <div className="space-y-1.5">
            <SkeletonBlock className="h-4 w-24 rounded" />
            <SkeletonBlock className="h-3 w-16 rounded" />
          </div>
          <SkeletonBlock className="h-8 w-20 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonRotation() {
  return (
    <div className="space-y-4">
      <div className="card space-y-3">
        <SkeletonBlock className="h-5 w-36 rounded" />
        <div className="overflow-x-auto">
          <div className="flex gap-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="min-w-[120px] space-y-2">
                <SkeletonBlock className="h-8 rounded-lg" />
                {[...Array(3)].map((_, j) => (
                  <SkeletonBlock key={j} className="h-10 rounded-lg" />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function SkeletonTableRows() {
  return (
    <div className="space-y-0">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="flex gap-3 px-3 py-2.5 border-b border-bg-border">
          {[...Array(6)].map((_, j) => (
            <SkeletonBlock key={j} className="h-3.5 flex-1 rounded" />
          ))}
        </div>
      ))}
    </div>
  );
}
