import type { Metadata } from "next";

const TITLE = "Privacy Policy";
const DESCRIPTION = "How Tulo collects, uses, and protects your information.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/privacy" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/privacy" },
};

const CONTACT_EMAIL = "info@tulo.io";
const LAST_UPDATED = "September 2026";

export default function PrivacyPolicyPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold">Privacy Policy</h1>
      <p className="mt-2 text-sm text-ink/50">Last updated: {LAST_UPDATED}</p>

      <div className="mt-6 space-y-8 text-ink/80">
        <section>
          <p>
            This policy explains what information Tulo (&ldquo;we,&rdquo; &ldquo;us&rdquo;)
            collects when you visit this site, how it&apos;s used, and the choices you have
            about it.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Information we collect</h2>
          <p className="mt-3">
            We don&apos;t require you to create an account or provide personal information to
            read recipes, use the tools, or browse the site. The information we do collect
            comes from two sources:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong className="text-ink">Usage data.</strong> Like most websites, our
              hosting and analytics providers automatically log standard technical
              information when you visit &mdash; your approximate location (derived from IP
              address), browser and device type, pages viewed, and how you arrived at the
              site. This is used in aggregate to understand what content is useful and to keep
              the site running reliably, not to identify you individually.
            </li>
            <li>
              <strong className="text-ink">Information you provide directly.</strong> If you
              email us through the{" "}
              <a href="/contact" className="underline hover:text-accent">
                Contact page
              </a>
              , we&apos;ll have whatever information you choose to include in that message
              (typically your email address and whatever you write to us).
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Cookies and similar technologies</h2>
          <p className="mt-3">
            This site uses cookies and similar technologies for two purposes: to remember
            simple preferences in your browser (like a unit or serving-size choice you made on
            a recipe), and, where advertising is enabled, to support the ad networks described
            below. You can block or delete cookies through your browser&apos;s settings; doing
            so may affect how well some features of the site work, but won&apos;t prevent you
            from reading content.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Advertising</h2>
          <p className="mt-3">
            Tulo may display ads served by third-party advertising companies, including Google.
            Google and its partners use cookies (including the DoubleClick cookie) to serve ads
            based on your prior visits to this and other websites. Google&apos;s use of
            advertising cookies enables it and its partners to serve ads based on your visit to
            this site and/or other sites on the Internet.
          </p>
          <p className="mt-3">
            You can opt out of personalized advertising by visiting{" "}
            <a
              href="https://adssettings.google.com"
              className="underline hover:text-accent"
              target="_blank"
              rel="noopener noreferrer"
            >
              Google Ads Settings
            </a>
            , or opt out of a participating third-party vendor&apos;s use of cookies for
            personalized advertising by visiting{" "}
            <a
              href="https://www.aboutads.info/choices"
              className="underline hover:text-accent"
              target="_blank"
              rel="noopener noreferrer"
            >
              aboutads.info/choices
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Other third-party services</h2>
          <p className="mt-3">
            Recipe and article photos on this site are sourced from Unsplash and Pexels, both
            of which may separately log requests for the images they serve. Where we use
            analytics tools to understand site traffic, those providers process the usage data
            described above under their own privacy policies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Your rights</h2>
          <p className="mt-3">
            Depending on where you live, you may have rights under data protection laws such
            as the GDPR (EU/UK) or the CCPA (California) &mdash; including the right to know
            what information is collected about you, to request its deletion, and to opt out
            of its sale or use for targeted advertising. Since we don&apos;t maintain user
            accounts or a persistent profile tied to your identity, most of these requests are
            best satisfied through the opt-out links above or your browser&apos;s own privacy
            controls. For anything else, contact us using the details below.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Children&apos;s privacy</h2>
          <p className="mt-3">
            This site is not directed at children under 13, and we do not knowingly collect
            personal information from children.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Changes to this policy</h2>
          <p className="mt-3">
            We may update this policy from time to time. The &ldquo;Last updated&rdquo; date
            at the top of this page reflects the most recent revision.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Contact</h2>
          <p className="mt-3">
            Questions about this policy or how your information is handled can be sent to{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="underline hover:text-accent">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>
      </div>
    </main>
  );
}
