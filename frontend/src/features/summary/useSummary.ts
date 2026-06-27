import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSummary } from '@/shared/api';

export function useSummary(documentId: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['summary', documentId],
    queryFn: () => getSummary(documentId),
    enabled: false, // only fetch when explicitly triggered or data already cached
    staleTime: Infinity, // never refetch — summary is immutable once generated
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => getSummary(documentId),
    onSuccess: (data) => {
      queryClient.setQueryData(['summary', documentId], data);
    },
  });

  return {
    summary: query.data ?? mutation.data,
    isLoading: mutation.isPending,
    isError: mutation.isError,
    generate: mutation.mutate,
  };
}
