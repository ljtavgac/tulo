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
            comes from three sources:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong className="text-ink">Log and device data.</strong> Like most websites,
              our hosting and analytics providers automatically log standard technical
              information when you visit &mdash; IP address (and the approximate location
              derived from it), browser type and version, operating system, device type,
              referring and exit pages, the pages you view, and the date and time of your
              visit. This is used in aggregate to understand what content is useful, diagnose
              problems, and keep the site running reliably, not to identify you individually.
            </li>
            <li>
              <strong className="text-ink">Information collected via cookies and similar
              technologies.</strong> Covered in more detail below &mdash; this includes
              preference cookies we set ourselves and cookies set by third-party services such
              as advertising and analytics providers.
            </li>
            <li>
              <strong className="text-ink">Information you provide directly.</strong> If you
              email us through the{" "}
              <a href="/contact" className="underline hover:text-accent">
                Contact page
              </a>
              , we&apos;ll have whatever information you choose to include in that message
              (typically your email address and whatever you write to us). We use this only to
              respond to you and don&apos;t add it to any marketing list without your consent.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Cookies and similar technologies</h2>
          <p className="mt-3">
            Cookies are small text files a site stores in your browser. We use a few different
            kinds:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong className="text-ink">Essential/preference cookies.</strong> Remember
              simple choices you make in your browser, like a unit or serving-size preference
              on a recipe, so you don&apos;t have to reset it on every visit.
            </li>
            <li>
              <strong className="text-ink">Analytics cookies.</strong> Help us understand
              which pages and features get used, in aggregate, so we can improve the site.
            </li>
            <li>
              <strong className="text-ink">Advertising cookies.</strong> Set by the ad
              networks described below to serve and measure ads, including ads based on your
              browsing activity across sites.
            </li>
          </ul>
          <p className="mt-3">
            You can control or delete cookies through your browser&apos;s settings, and most
            browsers let you block third-party cookies specifically while still allowing the
            site to function. Doing so may affect how well some features work (a serving-size
            preference won&apos;t persist between visits, for instance), but won&apos;t
            prevent you from reading content. We don&apos;t currently respond differently to
            browser &ldquo;Do Not Track&rdquo; signals, since there&apos;s no accepted
            standard for how sites should interpret them; the opt-out mechanisms listed under
            Advertising below are the most reliable way to control ad personalization.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Advertising</h2>
          <p className="mt-3">
            Tulo may display ads served by third-party advertising companies, including Google
            and its advertising partners. These companies use cookies and similar technologies
            (including the DoubleClick cookie) to serve ads based on your prior visits to this
            and other websites, and to measure how those ads perform. This means a third party
            may use non-personally-identifiable information about your visits here and to
            other sites to provide advertisements about goods and services that may interest
            you.
          </p>
          <p className="mt-3">
            You have several ways to control this:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              Opt out of Google&apos;s use of advertising cookies at{" "}
              <a
                href="https://adssettings.google.com"
                className="underline hover:text-accent"
                target="_blank"
                rel="noopener noreferrer"
              >
                Google Ads Settings
              </a>
              .
            </li>
            <li>
              Opt out of participating third-party vendors&apos; use of cookies for
              personalized advertising at{" "}
              <a
                href="https://www.aboutads.info/choices"
                className="underline hover:text-accent"
                target="_blank"
                rel="noopener noreferrer"
              >
                aboutads.info/choices
              </a>{" "}
              (US) or{" "}
              <a
                href="https://www.youronlinechoices.eu"
                className="underline hover:text-accent"
                target="_blank"
                rel="noopener noreferrer"
              >
                youronlinechoices.eu
              </a>{" "}
              (EU).
            </li>
            <li>
              Block third-party cookies entirely through your browser&apos;s privacy settings,
              which prevents ad-personalization cookies from being set in the first place.
            </li>
          </ul>
          <p className="mt-3">
            Opting out of personalized advertising doesn&apos;t mean you&apos;ll see fewer
            ads, only that the ads you see will be less targeted to your browsing activity.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Other third-party services</h2>
          <p className="mt-3">
            We use a small number of outside services to run the site, each of which processes
            data under its own privacy policy rather than ours:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong className="text-ink">Hosting and infrastructure.</strong> The site is
              served through third-party hosting and content-delivery providers, which
              necessarily process the log data described above to deliver pages to you.
            </li>
            <li>
              <strong className="text-ink">Image sourcing.</strong> Recipe and article photos
              are sourced from Unsplash and Pexels, both of which may separately log requests
              for the images they serve.
            </li>
            <li>
              <strong className="text-ink">Analytics.</strong> Where we use analytics tools to
              understand site traffic and usage patterns, those providers process the usage
              data described above.
            </li>
            <li>
              <strong className="text-ink">Advertising.</strong> Google and its advertising
              partners, as described in the Advertising section above.
            </li>
          </ul>
          <p className="mt-3">
            This site also links out to external sites we don&apos;t control (a recipe&apos;s
            source, an ingredient&apos;s retailer, and similar). Those sites have their own
            privacy practices, and we&apos;re not responsible for their content or policies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Data retention</h2>
          <p className="mt-3">
            Log and usage data is generally retained only as long as needed for the analytics
            and security purposes described above, on a schedule set by our hosting and
            analytics providers. Messages sent through the Contact page are kept as long as
            needed to address your inquiry and for a reasonable period afterward, in case you
            follow up.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Data security</h2>
          <p className="mt-3">
            We rely on reputable, industry-standard hosting and infrastructure providers, and
            all traffic to this site is encrypted in transit (HTTPS). That said, no method of
            transmission or storage is 100% secure, and we can&apos;t guarantee absolute
            security for any information transmitted to us.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">International data transfers</h2>
          <p className="mt-3">
            Our hosting, analytics, and advertising providers may process and store
            information in the United States or other countries outside your own. Where
            required, these providers rely on recognized legal mechanisms (such as Standard
            Contractual Clauses) to safeguard information transferred internationally.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Your rights</h2>
          <p className="mt-3">
            Depending on where you live, you may have rights under data protection laws such
            as the GDPR (EU/UK) or the CCPA/CPRA (California), including the right to:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>Know what categories of information we collect and how it&apos;s used;</li>
            <li>Request access to or a copy of information we hold about you;</li>
            <li>Request correction or deletion of your information;</li>
            <li>
              Opt out of the &ldquo;sale&rdquo; or &ldquo;sharing&rdquo; of your information
              (as those terms are defined under California law) for targeted advertising
              purposes, which for a site like this means opting out of ad-personalization
              cookies as described above;
            </li>
            <li>Object to or restrict certain processing of your information (GDPR); and</li>
            <li>
              Not be discriminated against for exercising any of these rights &mdash; we
              won&apos;t deny you service, charge different prices, or provide a different
              level of service for making a privacy request.
            </li>
          </ul>
          <p className="mt-3">
            Since we don&apos;t maintain user accounts or a persistent profile tied to your
            identity, most of these requests are best satisfied through the opt-out links
            above or your browser&apos;s own privacy controls. For anything else, including a
            formal access, deletion, or correction request, contact us using the details
            below; we&apos;ll respond within the timeframe required by applicable law.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Children&apos;s privacy</h2>
          <p className="mt-3">
            This site is not directed at children under 13, and we do not knowingly collect
            personal information from children. If you believe a child has provided us with
            personal information, contact us and we&apos;ll delete it.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Changes to this policy</h2>
          <p className="mt-3">
            We may update this policy from time to time as the site, our tools and providers,
            or applicable law change. The &ldquo;Last updated&rdquo; date at the top of this
            page reflects the most recent revision; material changes will be reflected here
            when they take effect.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink">Contact</h2>
          <p className="mt-3">
            Questions about this policy, or requests regarding how your information is
            handled, can be sent to{" "}
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
