import { ApiError, NetworkError } from '../api/types';

describe('ApiError', () => {
  it('stores code, message, and statusCode', () => {
    const err = new ApiError('NOT_FOUND', 'Resource not found.', 404);
    expect(err.code).toBe('NOT_FOUND');
    expect(err.message).toBe('Resource not found.');
    expect(err.statusCode).toBe(404);
    expect(err.name).toBe('ApiError');
    expect(err).toBeInstanceOf(Error);
  });
});

describe('NetworkError', () => {
  it('uses default message', () => {
    const err = new NetworkError();
    expect(err.message).toBe('Network request failed. Check your connection.');
    expect(err.name).toBe('NetworkError');
  });

  it('accepts custom message', () => {
    const err = new NetworkError('Request timed out.');
    expect(err.message).toBe('Request timed out.');
  });
});
