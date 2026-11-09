import { describe, expect, it } from 'vitest';
import { OperacionLocal } from '../offline.models';
import { numeroLocal } from './comprobante-provisional';

describe('B1 · comprobante provisional', () => {
  it('numera con LOC-<sucursal>-<6 del UUID>', () => {
    const o = { id: 'abc123de-0000-4000-8000-000000000000', sucursal_id: 2 } as OperacionLocal;
    expect(numeroLocal(o)).toBe('LOC-002-ABC123');
  });
});
