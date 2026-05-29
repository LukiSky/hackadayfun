export default function ReportCard() {
  return (
    <div className="rounded-soft bg-accentBlue p-6 text-cleanWhite">
      <h2 className="font-garage text-2xl">Generated Funder Report</h2>

      <div className="mt-4 space-y-3 font-proxima text-sm leading-6">
        <p>
          Lifechanger analysed 10,000 workshop sessions across Australian school
          partners, reaching 699,102 attending students.
        </p>

        <p>
          Students showed consistent improvement across wellbeing outcomes,
          including confidence, resilience, self-awareness, stress management,
          optimism, and peer connection.
        </p>

        <p>
          Feedback suggests students especially valued mentor storytelling,
          reflection activities, practical stress-management strategies, and
          opportunities to identify personal strengths.
        </p>
      </div>

      <button className="mt-5 rounded-full bg-cleanWhite px-5 py-3 font-garage text-sm text-inkBlack">
        Copy Report
      </button>
    </div>
  );
}