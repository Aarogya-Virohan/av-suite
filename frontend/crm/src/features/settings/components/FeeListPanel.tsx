'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Pencil, Plus, Trash2 } from 'lucide-react';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { SlideOver } from '../../../components/ui/SlideOver';
import { Badge, Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { formatMoney } from '../../../lib/money';
import { cn } from '../../../lib/cn';
import {
  FEE_CATEGORIES,
  type FeeCategory,
  type FeeItem,
  feeCategoryLabel,
  normalizePrice,
  useFeeItems,
  useRemoveFeeItem,
  useSaveFeeItem,
} from '../feeItems';

const errorText = 'mt-1.5 text-xs font-medium text-danger';

/**
 * Settings > Fee List (CRM-2). The clinic's standard charges; Create Invoice
 * offers them as ready lines. Writes are admin only on the server.
 */
export function FeeListPanel({ canEdit }: { canEdit: boolean }) {
  const { data: items = [], isLoading } = useFeeItems();
  const remove = useRemoveFeeItem();
  const [editing, setEditing] = useState<FeeItem | 'new' | null>(null);

  const columns: Column<FeeItem>[] = [
    { key: 'name', header: 'Fee item', render: (f) => <span className="font-semibold text-ink">{f.name}</span> },
    { key: 'category', header: 'Category', render: (f) => <Badge tone="neutral">{feeCategoryLabel(f.category)}</Badge> },
    {
      key: 'default_price',
      header: 'Default price',
      render: (f) => <span className="whitespace-nowrap font-semibold tabular-nums text-ink">{formatMoney(f.default_price)}</span>,
    },
    {
      key: 'price_editable',
      header: 'Price on invoice',
      render: (f) => (f.price_editable ? <span className="text-xs text-muted">Can change</span> : <Badge tone="info">Fixed</Badge>),
    },
  ];
  if (canEdit) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      render: (f) => (
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setEditing(f)}
            aria-label={`Edit ${f.name}`}
            className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-ink-2 hover:bg-canvas"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            type="button"
            disabled={remove.isPending}
            onClick={async () => {
              if (!window.confirm(`Remove "${f.name}" from the fee list? Old invoices keep their lines.`)) return;
              try {
                await remove.mutateAsync(f.id);
                toast.success(`${f.name} removed`);
              } catch (err: any) {
                toast.error(err?.message || 'Could not remove the fee item');
              }
            }}
            aria-label={`Remove ${f.name}`}
            className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-danger hover:bg-danger-wash disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    });
  }

  const nextSort = items.reduce((m, f) => Math.max(m, f.sort_order), 0) + 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-sm text-muted">
          Standard charges of your clinic. They show up under &quot;Add fee item&quot; when you create an invoice.
        </p>
        {canEdit && (
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" />
            <span>Add Fee Item</span>
          </Button>
        )}
      </div>
      <DataTable
        columns={columns}
        data={items}
        isLoading={isLoading}
        searchField={(f) => `${f.name} ${feeCategoryLabel(f.category)}`}
        searchPlaceholder="Search fee items..."
        emptyMessage="No fee items yet. Add your consultation and session charges."
      />
      <FeeItemSlideOver
        item={editing === 'new' ? null : editing}
        isOpen={editing !== null}
        nextSort={nextSort}
        onClose={() => setEditing(null)}
      />
    </div>
  );
}

function FeeItemSlideOver({
  item,
  isOpen,
  nextSort,
  onClose,
}: {
  item: FeeItem | null;
  isOpen: boolean;
  nextSort: number;
  onClose: () => void;
}) {
  const save = useSaveFeeItem();
  const [name, setName] = useState('');
  const [category, setCategory] = useState<FeeCategory>('consultation');
  const [price, setPrice] = useState('');
  const [editable, setEditable] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});

  React.useEffect(() => {
    if (!isOpen) return;
    setName(item?.name ?? '');
    setCategory(item?.category ?? 'consultation');
    setPrice(item ? String(Number(item.default_price)) : '');
    setEditable(item?.price_editable ?? true);
    setErrors({});
  }, [isOpen, item]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = 'Name is required';
    const normalized = normalizePrice(price);
    if (normalized == null) next.price = 'Enter a price, e.g. 800 or 799.50';
    setErrors(next);
    if (Object.keys(next).length) return;
    try {
      await save.mutateAsync({
        id: item?.id,
        values: {
          name: name.trim(),
          category,
          default_price: normalized as string,
          price_editable: editable,
          ...(item ? {} : { sort_order: nextSort }),
        },
      });
      toast.success(item ? 'Fee item updated' : 'Fee item added');
      onClose();
    } catch (err: any) {
      toast.error(err?.message || 'Could not save the fee item');
    }
  };

  return (
    <SlideOver
      isOpen={isOpen}
      onClose={onClose}
      title={item ? 'Edit Fee Item' : 'Add Fee Item'}
      subtitle="Shown as a ready line on Create Invoice"
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div>
          <FieldLabel htmlFor="fee-name">Name *</FieldLabel>
          <input
            id="fee-name"
            value={name}
            maxLength={255}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Physiotherapy session"
            className={cn(inputClass, errors.name && 'border-danger')}
          />
          {errors.name && <p className={errorText}>{errors.name}</p>}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="fee-category">Category *</FieldLabel>
            <select id="fee-category" value={category} onChange={(e) => setCategory(e.target.value as FeeCategory)} className={inputClass}>
              {FEE_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <FieldLabel htmlFor="fee-price">Default price (₹) *</FieldLabel>
            <input
              id="fee-price"
              inputMode="decimal"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="800"
              className={cn(inputClass, errors.price && 'border-danger')}
            />
            {errors.price && <p className={errorText}>{errors.price}</p>}
          </div>
        </div>
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-canvas p-3">
          <input type="checkbox" checked={editable} onChange={(e) => setEditable(e.target.checked)} className="mt-0.5 h-4 w-4 accent-grove" />
          <span className="text-sm">
            <span className="font-semibold text-ink">Staff can change the price on an invoice</span>
            <span className="block text-xs text-muted">Untick to keep this price fixed when it is added to an invoice.</span>
          </span>
        </label>
        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>{item ? 'Save Changes' : 'Add Fee Item'}</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
