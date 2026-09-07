import JsonLd from "./JsonLd";
import type { Faq } from "@/lib/types";

export default function FaqSection({ faqs }: { faqs?: Faq[] }) {
  if (!faqs || faqs.length === 0) return null;

  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: faqs.map((faq) => ({
            "@type": "Question",
            name: faq.question,
            acceptedAnswer: { "@type": "Answer", text: faq.answer },
          })),
        }}
      />
      <h2 className="mt-8 text-xl font-bold">FAQ</h2>
      <div className="mt-3 space-y-4">
        {faqs.map((faq, i) => (
          <div key={i}>
            <p className="font-semibold">{faq.question}</p>
            <p className="mt-1 text-sm text-ink/80">{faq.answer}</p>
          </div>
        ))}
      </div>
    </>
  );
}
