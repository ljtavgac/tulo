import Image from "next/image";

export default function Logo({
  variant,
  className,
}: {
  variant: "light" | "dark";
  className?: string;
}) {
  // "light" variant = dark wordmark, for light-background contexts.
  // "dark" variant = cream wordmark, for dark-background contexts.
  const src = variant === "light" ? "/brand/tulo-light.png" : "/brand/tulo-dark.png";
  return (
    <Image
      src={src}
      alt="Tulo"
      width={110}
      height={80}
      className={className}
      priority
    />
  );
}
