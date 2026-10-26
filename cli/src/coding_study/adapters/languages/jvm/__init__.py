"""Java and Kotlin adapters: stub generators and one JVM runner for both languages."""

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm.gradle import WrapperGradle, default_gradle_user_home
from coding_study.adapters.languages.jvm.runner import WORKSPACE, JvmRunner
from coding_study.adapters.languages.jvm.stubs import JavaStubGenerator, KotlinStubGenerator
from coding_study.application.ports import LanguageRunner, StubGenerator
from coding_study.domain.problem import Language


def create_java_stub_generator() -> StubGenerator:
    return JavaStubGenerator()


def create_kotlin_stub_generator() -> StubGenerator:
    return KotlinStubGenerator()


def create_java_runner(context: LanguageContext) -> LanguageRunner:
    return _create_runner(context, Language.JAVA)


def create_kotlin_runner(context: LanguageContext) -> LanguageRunner:
    return _create_runner(context, Language.KOTLIN)


def _create_runner(context: LanguageContext, language: Language) -> JvmRunner:
    gradle = WrapperGradle(context.workspace / WORKSPACE, default_gradle_user_home())
    return JvmRunner(context, language, gradle)
