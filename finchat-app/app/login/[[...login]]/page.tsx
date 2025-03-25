import { SignIn } from "@clerk/nextjs"

export default function LoginPage() {
  return (
    <div 
      className="flex justify-center items-center h-screen bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/images/bgimage.jpg')" }}
    >
      <SignIn forceRedirectUrl="/chat"/>
    </div>
  )
}
