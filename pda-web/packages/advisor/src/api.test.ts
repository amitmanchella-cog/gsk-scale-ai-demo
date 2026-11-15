import { describe, expect, it, vi } from 'vitest';
import { api, ApiError, toApiError } from './api';
import { protocol, samples, stubApi } from './test-data';

describe('api', () => {
  it('uploads the file as multipart form data', async () => {
    const calls = stubApi({ '/api/protocols': { status: 201, body: protocol } });
    const result = await api.upload(new File(['text'], 'weak.txt'));
    expect(result.id).toBe('p-1');
    expect(calls[0]?.init?.method).toBe('POST');
    expect((calls[0]?.init?.body as FormData).get('file')).toBeInstanceOf(File);
  });

  it('turns a sample into a File with its own name', async () => {
    stubApi({ '/api/samples/t2d_phase3_weak': { body: 'Title: Diabetes study' } });
    const file = await api.sampleFile(samples[1]!);
    expect(file.name).toBe('t2d_phase3_weak.txt');
    expect(await file.text()).toBe('Title: Diabetes study');
  });

  it('fails when a sample is missing', async () => {
    stubApi({});
    await expect(api.sampleFile(samples[0]!)).rejects.toMatchObject({ status: 404 });
  });

  it('reads the reason from FastAPI error bodies', async () => {
    stubApi({
      '/api/protocols/x': { status: 404, body: { detail: 'Protocol not found' } },
      '/api/protocols': {
        status: 422,
        body: { detail: { message: 'No design found', warnings: ['Could not extract indication.'] } },
      },
    });
    await expect(api.protocol('x')).rejects.toMatchObject({ status: 404, message: 'Protocol not found' });
    await expect(api.upload(new File([''], 'a.txt'))).rejects.toMatchObject({
      message: 'No design found',
      warnings: ['Could not extract indication.'],
    });
  });

  it('falls back to a generic message', () => {
    expect(toApiError(500, null).message).toBe('Request failed (500)');
    expect(toApiError(422, { detail: [{ msg: 'field required' }] }).message).toBe('Request failed (422)');
    expect(toApiError(422, { detail: {} }).message).toBe('Request failed (422)');
  });

  it('explains when the API is unreachable', async () => {
    vi.stubGlobal('fetch', () => Promise.reject(new TypeError('Failed to fetch')));
    const error = await api.samples().catch((cause: unknown) => cause);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toContain('cannot be reached');
  });
});
