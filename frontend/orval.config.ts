import { defineConfig } from 'orval';

export default defineConfig({
  parisportif: {
    input: {
      target: './openapi.json',
    },
    output: {
      mode: 'tags-split',
      target: 'src/lib/api/endpoints',
      schemas: 'src/lib/api/models',
      client: 'react-query',
      httpClient: 'fetch',
      override: {
        mutator: {
          path: 'src/lib/api/custom-instance.ts',
          name: 'customInstance',
        },
        // Use camelCase for property names in generated types
        query: {
          useQuery: true,
          useMutation: true,
          signal: true,
        },
      },
    },
  },
});
