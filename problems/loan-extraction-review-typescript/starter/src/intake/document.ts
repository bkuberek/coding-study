// The source document: the fields of an application form, as text, the way the form was filled in.
// It comes from our own document store, so it is well formed, whatever its fields say.

export interface SourceDocument {
  documentId: string;
  fields: Record<string, string>;
}

export function parseDocument(text: string): SourceDocument {
  return JSON.parse(text) as SourceDocument;
}
