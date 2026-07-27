import { BRAND } from "@/lib/brand";

type LogoProps = {
  variant?: "light" | "dark" | "mark";
  className?: string;
  showWordmark?: boolean;
};

export function Logo({
  variant = "dark",
  className = "",
  showWordmark = true,
}: LogoProps) {
  const markColor = variant === "light" ? "#FFFFFF" : "var(--primary)";
  const textColor = variant === "light" ? "text-white" : "text-text-primary";

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        width="36"
        height="36"
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <rect width="36" height="36" rx="10" fill={variant === "light" ? "rgba(255,255,255,0.15)" : "var(--primary-soft)"} />
        <path
          d="M10 12.5h10.5a4.5 4.5 0 0 1 0 9H10V12.5Z"
          stroke={markColor}
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path
          d="M10 21.5h8"
          stroke={markColor}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M24.5 14c1.8 1.2 2.8 2.8 2.8 4.5s-1 3.3-2.8 4.5"
          stroke={markColor}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M27.2 12c2.4 1.7 3.8 3.9 3.8 6.5s-1.4 4.8-3.8 6.5"
          stroke={markColor}
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.55"
        />
      </svg>
      {showWordmark && (
        <span className={`text-lg font-semibold tracking-tight ${textColor}`}>
          {BRAND.name}
        </span>
      )}
    </span>
  );
}
