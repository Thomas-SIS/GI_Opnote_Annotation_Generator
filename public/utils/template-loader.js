/* TemplateLoader
Utility to fetch component HTML templates without a build step.
*/

export async function loadTemplate(relativePath, importerUrl) {
  const templateUrl = new URL(relativePath, importerUrl).toString();
  const response = await fetch(templateUrl);
  if (!response.ok) {
    throw new Error(`Unable to load template ${relativePath}`);
  }
  return response.text();
}
