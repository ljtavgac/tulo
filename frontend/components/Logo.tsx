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
  // width/height only set the intrinsic ratio for CLS -- visible size comes
  // from the caller's height class + w-auto (see call sites). tulo-dark.png
  // is cropped tight to its wordmark (533x295); tulo-light.png still has
  // its original canvas padding, hence the different ratio here.
  const [width, height] = variant === "light" ? [110, 80] : [533, 295];
  return (
    <Image
      src={src}
      alt="Tulo"
      width={width}
      height={height}
      className={className}
      priority
    />
  );
}
