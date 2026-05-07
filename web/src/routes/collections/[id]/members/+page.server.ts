import { redirect } from '@sveltejs/kit';

export function load({ params }: { params: Record<string, string> }) {
    redirect(302, `/collections/${params.id}`);
}
