import { Suspense } from 'react';
import ClientPage from './client-page';

export default function Page() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <ClientPage />
        </Suspense>
    );
}
