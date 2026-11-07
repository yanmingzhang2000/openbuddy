/**
 * FrameMind Brand Logo - Full Logo with Wordmark
 *
 * Includes the brand mark and "FrameMind" text.
 * Supports full and compact variants.
 */

import BrandMark, { type BrandMarkSize } from "./BrandMark";

type Props = {
  variant?: "full" | "compact";
  size?: "small" | "medium" | "large";
  showTagline?: boolean;
  className?: string;
};

const SIZE_CONFIG = {
  small: 24,
  medium: 32,
  large: 48,
} as const satisfies Record<NonNullable<Props["size"]>, BrandMarkSize>;

export default function BrandLogo({
  variant = "full",
  size = "medium",
  showTagline = false,
  className = "",
}: Props) {
  return (
    <span className={`brand-logo brand-logo--${size} brand-logo--${variant} ${className}`.trim()}>
      <span className="brand-logo__main">
        <BrandMark size={SIZE_CONFIG[size]} decorative />
        {variant === "full" && (
          <span className="brand-logo__copy">
            <span className="brand-logo__wordmark">FrameMind</span>
            {showTagline && <span className="brand-logo__tagline">Clarity before action</span>}
          </span>
        )}
      </span>
    </span>
  );
}
