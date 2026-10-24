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
  const markColor = variant === "light" ? "#FFFFFF" : "#FFFFFF";
  const textColor = variant === "light" ? "text-white" : "text-text-primary";

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        width="34"
        height="34"
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <rect
          width="36"
          height="36"
          rx="9"
          fill={variant === "light" ? "#2563eb" : "#0b1220"}
        />
        <rect
          x="0.5"
          y="0.5"
          width="35"
          height="35"
          rx="8.5"
          stroke="rgba(255,255,255,0.16)"
        />
        <path
          d="M10.5 12.5h10a4.5 4.5 0 0 1 0 9h-10V12.5Z"
          stroke={markColor}
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path
          d="M10.5 21.5h7.5"
          stroke={markColor}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M24.2 14c1.7 1.2 2.7 2.8 2.7 4.5s-1 3.3-2.7 4.5"
          stroke="#60a5fa"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M27 12c2.3 1.7 3.6 3.9 3.6 6.5S29.3 23.3 27 25"
          stroke="#93c5fd"
          strokeWidth="1.75"
          strokeLinecap="round"
          opacity="0.75"
        />
      </svg>
      {showWordmark && (
        <span className={`text-[1.05rem] font-semibold tracking-[-0.03em] ${textColor}`}>
          {BRAND.name}
        </span>
      )}
    </span>
  );
}
