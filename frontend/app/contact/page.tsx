import type { Metadata } from "next";
import { getPage } from "@/lib/api";
import type { StaticPageContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";

const TITLE = "Contact";
const DESCRIPTION = "Get in touch with Tulo.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/contact" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/contact" },
};

const CONTACT_EMAIL = "info@tulo.io";

export default async function ContactPage() {
  const page = await getPage<StaticPageContent>("contact");

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold">Contact</h1>

      {page ? (
        <StockPhotoSlot
          query={page.content.hero_image_query}
          imageUrl={page.content.image_url}
          attribution={page.content.image_attribution}
          className="mt-6"
        />
      ) : null}

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
          . We read every message and try to respond as quickly as we can.
        </p>
        <p>
          For press, partnership, or advertising inquiries, please use the same address and
          let us know what you&apos;re reaching out about in the subject line.
        </p>
      </div>
    </main>
  );
}
