/**
 * FrameMind Brand Mark - Icon Component
 *
 * A simple, original brand mark using SVG that combines:
 * - Four framing corners (representing "framing" the problem)
 * - Central focus point (representing clarity and intent)
 * - Clean, minimal aesthetic
 */

export type BrandMarkSize = 24 | 32 | 48;

type Props = {
  size?: BrandMarkSize;
  primaryColor?: string;
  className?: string;
  decorative?: boolean;
};

export default function BrandMark({
  size = 32,
  primaryColor = "var(--primary)",
  className = "",
  decorative = false,
}: Props) {
  const strokeWidth = size <= 24 ? 2 : size <= 32 ? 2.5 : 3;
  const cornerSize = size * 0.35;
  const centerRadius = size * 0.08;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role={decorative ? undefined : "img"}
      aria-label={decorative ? undefined : "FrameMind"}
      aria-hidden={decorative ? true : undefined}
      focusable="false"
    >
      {/* Top-left corner */}
      <path
        d={`M ${strokeWidth} ${cornerSize} L ${strokeWidth} ${strokeWidth} L ${cornerSize} ${strokeWidth}`}
        stroke={primaryColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Top-right corner */}
      <path
        d={`M ${size - cornerSize} ${strokeWidth} L ${size - strokeWidth} ${strokeWidth} L ${size - strokeWidth} ${cornerSize}`}
        stroke={primaryColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Bottom-right corner */}
      <path
        d={`M ${size - strokeWidth} ${size - cornerSize} L ${size - strokeWidth} ${size - strokeWidth} L ${size - cornerSize} ${size - strokeWidth}`}
        stroke={primaryColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Bottom-left corner */}
      <path
        d={`M ${cornerSize} ${size - strokeWidth} L ${strokeWidth} ${size - strokeWidth} L ${strokeWidth} ${size - cornerSize}`}
        stroke={primaryColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Center focus point */}
      <circle cx={size / 2} cy={size / 2} r={centerRadius} fill={primaryColor} />
    </svg>
  );
}
