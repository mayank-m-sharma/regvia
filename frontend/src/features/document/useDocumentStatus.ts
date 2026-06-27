import { useQuery } from '@tanstack/react-query';
import { getDocumentStatus } from '@/shared/api';

export function useDocumentStatus(documentId: string | null) {
  return useQuery({
    queryKey: ['document', documentId],
    queryFn: () => getDocumentStatus(documentId!),
    enabled: documentId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'ready' || status === 'failed') return false;
      return 2000;
    },
  });
}
