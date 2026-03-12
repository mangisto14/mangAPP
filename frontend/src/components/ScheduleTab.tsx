const PERIODS = [
  "08/3–10/3",
  "10/3–12/3",
  "13/3–15/3",
  "15/3–17/3",
  "17/3–19/3",
  "20/3–22/3",
  "22/3–24/3",
  "24/3–26/3",
  "27/3–29/3",
];

type RowData = {
  role: string;
  cells: string[][];
};

const ROWS: RowData[] = [
  {
    role: "קצינים",
    cells: [
      ["טל"],
      ["זיו"],
      ["שלמה"],
      ["זיו"],
      ["שלמה"],
      ["טל"],
      ["שלמה"],
      ["טל"],
      ["זיו"],
    ],
  },
  {
    role: "מפקדים",
    cells: [
      ["יוסף"],
      ["בועז"],
      ["אביתר"],
      ["בועז"],
      ["אביתר"],
      ["יוסף"],
      ["אביתר"],
      ["יוסף"],
      ["בועז"],
    ],
  },
  {
    role: "פקחים",
    cells: [
      ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],
      ["חן", "גיל שמואל", "ירין"],
      ["דדון", "שלומי", "טלקר", "ביטון"],
      ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],
      ["דדון", "שלומי", "טלקר", "ביטון"],
      ["חן", "גיל בוחניק", "ירין"],
      ["דדון", "שלומי", "טלקר", "ביטון"],
      ["חן", "גיל בוחניק", "ירין"],
      ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],
    ],
  },
  {
    role: "נהגים",
    cells: [
      ["גיל", "עוז"],
      ["ישראל", "רומן"],
      ["מתנאל", "נוני"],
      ["גיל", "עוז"],
      ["מתנאל", "נוני"],
      ["ישראל", "רומן"],
      ["מתנאל", "נוני"],
      ["ישראל", "רומן"],
      ["גיל", "עוז"],
    ],
  },
  {
    role: "מטהרים",
    cells: [
      ["אסף", "אליאב"],
      ["נדב", "לירן", "גל"],
      ["עמיר", "שלומי ס"],
      ["אסף", "אליאב"],
      ["עמיר", "שלומי ס"],
      ["נדב", "לירן", "גל"],
      ["עמיר", "שלומי ס"],
      ["נדב", "לירן", "גל"],
      ["אסף", "אליאב"],
    ],
  },
  {
    role: "עתודאים",
    cells: [
      ["שי שני", "דוד סויסה", "יובל מועלם", "טל ברוקר"],
      ["יהונתן פריאל", "אור הדר", "אריאל קרליך"],
      ["רועי נגאוקר", "מתן קזז", "תומר שמאי"],
      ["יהונתן פריאל", "אור הדר", "אריאל קרליך"],
      ["רועי נגאוקר", "מתן קזז", "תומר שמאי"],
      ["שי שני", "דוד סויסה", "יובל מועלם", "טל ברוקר"],
      ["רועי נגאוקר", "מתן קזז", "תומר שמאי"],
      ["שי שני", "דוד סויסה", "יובל מועלם", "טל ברוקר"],
      ["יהונתן פריאל", "אור הדר", "אריאל קרליך"],
    ],
  },
];

// Color groups for alternating visual identity per role
const ROLE_COLORS: Record<string, string> = {
  "קצינים":   "bg-blue-500/10 border-blue-500/20 text-blue-300",
  "מפקדים":   "bg-purple-500/10 border-purple-500/20 text-purple-300",
  "פקחים":    "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
  "נהגים":    "bg-amber-500/10 border-amber-500/20 text-amber-300",
  "מטהרים":   "bg-rose-500/10 border-rose-500/20 text-rose-300",
  "עתודאים":  "bg-sky-500/10 border-sky-500/20 text-sky-300",
};

export default function ScheduleTab() {
  return (
    <div className="fade-in space-y-3" dir="rtl">
      <h2 className="text-base font-bold text-text">לוח סבב – מרץ 2025</h2>

      {/* Horizontal scroll wrapper */}
      <div className="overflow-x-auto rounded-xl border border-bg-border">
        <table className="min-w-max w-full text-xs border-collapse">
          {/* Header */}
          <thead>
            <tr className="bg-bg-card">
              <th className="sticky right-0 z-10 bg-bg-card border border-bg-border px-3 py-2 text-right font-bold text-text-muted min-w-[80px]">
                תפקיד
              </th>
              {PERIODS.map((p) => (
                <th
                  key={p}
                  className="border border-bg-border px-3 py-2 text-center font-bold text-primary-light whitespace-nowrap min-w-[110px]"
                >
                  {p}
                </th>
              ))}
            </tr>
          </thead>

          {/* Body */}
          <tbody>
            {ROWS.map((row, ri) => (
              <tr
                key={row.role}
                className={ri % 2 === 0 ? "bg-bg-deep" : "bg-bg-base"}
              >
                {/* Role label */}
                <td className="sticky right-0 z-10 border border-bg-border px-3 py-2 font-bold text-text bg-inherit">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-md border text-xs font-bold ${ROLE_COLORS[row.role] ?? ""}`}
                  >
                    {row.role}
                  </span>
                </td>

                {/* Data cells */}
                {row.cells.map((names, ci) => (
                  <td
                    key={ci}
                    className="border border-bg-border px-2 py-1.5 text-center align-top"
                  >
                    <div className="flex flex-col gap-0.5">
                      {names.map((name) => (
                        <span
                          key={name}
                          className="text-text text-xs leading-snug"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
