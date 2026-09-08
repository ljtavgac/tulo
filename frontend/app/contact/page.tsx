import type { Metadata } from "next";

const TITLE = "Contact";
const DESCRIPTION = "Get in touch with Tulo.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/contact" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/contact" },
};

const CONTACT_EMAIL = "info@tulo.io";

export default function ContactPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold">Contact</h1>

      <div className="mt-6 space-y-4 text-ink/80">
        <p>
          Found something wrong with a recipe, spotted a broken link, or have a suggestion for
          what we should cover next? We&apos;d like to hear about it.
        </p>
        <p>
          Email us at{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="underline hover:text-accent">
            {CONTACT_EMAIL}
          </a>
          . We read every message, though as a small, independent site we can&apos;t always
          promise a fast reply.
        </p>
        <p>
          For press, partnership, or advertising inquiries, please use the same address and
          let us know what you&apos;re reaching out about in the subject line.
        </p>
      </div>
    </main>
  );
}
