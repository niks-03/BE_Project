import HeroSection from "@/app/landingPageComponents/hero-section";
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Bot, ChartArea } from 'lucide-react'
import Link from "next/link";
import { ReactNode } from 'react'

export default function Home() {
  return (
    <div>
      <HeroSection/>
      <section className="bg-zinc-50 py-16 md:py-32 dark:bg-transparent">
    <div className="@container mx-auto max-w-5xl px-6">
      <div className="text-center">
        <h2 className="text-balance text-4xl font-semibold lg:text-5xl">Built to cover your needs</h2>
        <p className="mt-4">Analyze and Visualize your financial data at one place</p>
      </div>
      
      {/* Modified container for cards - center aligned */}
      <div className="mt-8 md:mt-16 flex flex-col md:flex-row gap-6 justify-center items-center">
        <Link href="/chat">
          <Card className="group shadow-zinc-950/5 max-w-sm dark:bg-transparent">
            <CardHeader className="pb-3">
              <CardDecorator>
                <Bot className="size-8" aria-hidden />
              </CardDecorator>

              <h3 className="mt-6 font-medium text-center">Chat with Doc</h3>
            </CardHeader>

            <CardContent>
              <p className="text-sm">Use the feature to do conversation with your Financial document.</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/visualize">
          <Card className="group shadow-zinc-950/5 max-w-sm dark:bg-transparent">
            <CardHeader className="py-0">
              <CardDecorator>
                <ChartArea className="size-8" aria-hidden />
              </CardDecorator>

              <h3 className="mt-6 font-medium text-center">Visualize the Data</h3>
            </CardHeader>

            <CardContent>
              <p className="mt-3 text-sm">Use the feature to Visualize the financial data with graphs and charts. </p>
            </CardContent>
          </Card>
        </Link>

      </div>
    </div>
  </section>
    </div>
  );
}

const CardDecorator = ({ children }: { children: ReactNode }) => (
  <div className="relative mx-auto size-36 duration-200 [--color-border:color-mix(in_oklab,var(--color-zinc-950)10%,transparent)] group-hover:[--color-border:color-mix(in_oklab,var(--color-zinc-950)20%,transparent)] dark:[--color-border:color-mix(in_oklab,var(--color-white)15%,transparent)] dark:group-hover:bg-white/5 dark:group-hover:[--color-border:color-mix(in_oklab,var(--color-white)20%,transparent)]">
      <div aria-hidden className="absolute inset-0 bg-[linear-gradient(to_right,var(--color-border)_1px,transparent_1px),linear-gradient(to_bottom,var(--color-border)_1px,transparent_1px)] bg-[size:24px_24px]" />
      <div aria-hidden className="bg-radial to-background absolute inset-0 from-transparent to-75%" />
      <div className="bg-background absolute inset-0 m-auto flex size-12 items-center justify-center border-l border-t">{children}</div>
  </div>
)