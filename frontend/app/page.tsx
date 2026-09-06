import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>Tulo</h1>
      <p>
        <Link href="/food">Go to the food section</Link>
      </p>
    </main>
  );
}
