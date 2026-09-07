import type { Metadata } from "next";
import RecipeGeneratorClient from "./RecipeGeneratorClient";

const TITLE = "Custom Recipe Generator";
const DESCRIPTION =
  "Tell us what's in your kitchen and get a recipe idea back -- a custom recipe generator built around the ingredients you already have.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/tools/recipe-generator" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/tools/recipe-generator" },
};

export default function RecipeGeneratorPage() {
  return <RecipeGeneratorClient />;
}
