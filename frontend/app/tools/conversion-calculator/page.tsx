import type { Metadata } from "next";
import ConversionCalculatorClient from "./ConversionCalculatorClient";

const TITLE = "Kitchen Measurement Conversion Calculator";
const DESCRIPTION =
  "Free kitchen measurement conversion calculator -- convert cups, tablespoons, grams, ounces, and oven temperatures between US and metric.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/tools/conversion-calculator" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/tools/conversion-calculator" },
};

export default function ConversionCalculatorPage() {
  return <ConversionCalculatorClient />;
}
