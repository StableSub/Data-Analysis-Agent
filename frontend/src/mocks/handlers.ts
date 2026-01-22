import { http, HttpResponse } from 'msw';

export const handlers = [
  // Chat message mock
  http.post('/api/chat', async ({ request }) => {
    const body = await request.json().catch(() => ({}));
    const message = body?.message ?? '';
    return HttpResponse.json({
      reply: `모킹된 응답입니다: ${message}`,
    });
  }),

  // Datasets list mock
  http.get('/api/datasets', () => {
    return HttpResponse.json({
      items: [
        { id: 'ds_1', name: 'manufacturing_data_2024.csv', rows: 15234 },
        { id: 'ds_2', name: 'quality_metrics.xlsx', rows: 8912 },
      ],
    });
  }),
];

